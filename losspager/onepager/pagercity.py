#!/usr/bin/env python

# stdlib imports

# third  party imports
import numpy as np
from impactutils.mapping.city import Cities
import pandas as pd

# local imports


def sort_data_frame(df, columns, ascending=True):
    """Sort a Pandas dataframe, taking into account the version of Pandas being used.

    :param df:
      Input DataFrame to be sorted.
    :param columns:
      string name or list of names which refer to the columns by which the data should be sorted.
    :param ascending:
      Boolean indicating whether the sort should be ascending or descending.
    :returns:
      Sorted DataFrame.
    """
    if pd.__version__ < "0.17.0":
        df = df.sort(columns=columns, ascending=ascending)
    else:
        df = df.sort_values(by=columns, ascending=ascending)
    return df


def _flag_map_cities(rows, mapcities):
    on_map = np.zeros(len(rows))
    mapnames = mapcities._dataframe["name"]
    i = 0
    for index, row in rows.iterrows():
        if mapnames.isin([row["name"]]).any():
            on_map[i] = 1
        i += 1

    rows["on_map"] = on_map
    return rows


class PagerCities(object):
    def __init__(self, cities, mmigrid):
        """Create a PagerCities object with a MapIO Cities instance and a Grid2 object containing MMI data.

        :param cities:
          BasemapCities instance.
        :param mmigrid:
          Grid2 object containing MMI data from a ShakeMap.
        """
        xmin, xmax, ymin, ymax = mmigrid.getBounds()
        dataframe = cities.limitByBounds((xmin, xmax, ymin, ymax)).getDataFrame()
        lat = dataframe["lat"].values
        lon = dataframe["lon"].values
        mmi = mmigrid.getValue(lat, lon)
        dataframe["mmi"] = mmi
        self._cities = Cities(dataframe)

    def getCityTable(self, mapcities):
        """
        Return a list of cities suitable for the onePAGER table of cities.

        The PAGER city sorting algorithm can be defined as follows.
        1. Sort cities by inverse intensity.  Select N (up to 6) from beginning of list.  If N < 6, return.
        2. Sort cities by capital status and population, and select M (up to 5) from beginning of the list that are not in the first list.
           If N+M == 11, sort selected cities by MMI, return list
        3. If N+M < 11, sort cities by inverse population, then select (up to) P= 11 - (M+N) cities that are not already in the list.  Combine
           list of P cities with list of N and list of M.
        4. Sort combined list of cities by inverse MMI and return.

        :param mapcities:
          MapIO Cities instance which contains list of cities that have been rendered on PAGER exposure map.
        :returns: DataFrame of up to 11 cities, sorted by algorithm described above.  'on_map' column indicates
                  whether the city also was found in the input mapcities.
        """
        # pandas changed how dataframes get sorted, so we have a convenience function here to hide the
        # ugliness
        # 1. Sort cities by inverse intensity.  Select N (up to 6) from beginning of list.  If N < 6, return.
        df = self._cities.getDataFrame()
        df = sort_data_frame(df, "mmi", ascending=False)
        if len(df) >= 6:
            rows = df.iloc[0:6]
            df = df.iloc[6:]
        else:
            df = sort_data_frame(df, "pop", ascending=True)
            df = _flag_map_cities(df, mapcities)
            return df

        # 2. Sort cities by capital status and population, and select M (up to 5) from beginning of the list that are not in the first list.
        #   If N+M == 11, sort selected cities by MMI, return list
        N = len(rows)
        df = sort_data_frame(df, ["iscap", "pop"], ascending=False)
        if len(df) >= 5:
            rows = pd.concat([rows, df.iloc[0:5]])
            df = df.iloc[5:]
            if len(rows) == 11:
                rows = sort_data_frame(rows, "mmi", ascending=False)
                rows = _flag_map_cities(rows, mapcities)
                return rows
        else:
            rows = pd.concat([rows, df])
            rows = sort_data_frame(rows, "mmi", ascending=False)
            rows = _flag_map_cities(rows, mapcities)
            return rows

        # 3. If N+M < 11, sort cities by inverse population, then select (up to) P= 11 - (M+N) cities that are
        #    not already in the list.  Combine list of P cities with list of N and list of M.
        df = sort_data_frame(df, "pop", ascending=False)
        MN = len(df)
        P = 11 - (MN)
        rows = pd.concat([rows, df[0:P]])

        # 4. Sort combined list of cities by inverse MMI and return.
        rows = sort_data_frame(rows, "mmi", ascending=False)

        # Add a column indicating whether the city was rendered on the map
        rows = _flag_map_cities(rows, mapcities)
        return rows

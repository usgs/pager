#!/usr/bin/env python

# stdlib imports
import os.path
from collections import OrderedDict

# third party imports
import pandas as pd
import numpy as np
from impactutils.colors.cpalette import ColorPalette
from openquake.hazardlib.geo.geodetic import geodetic_distance

# number of seconds to compare one event with another when searching for similar events.
TIME_WINDOW = 15
MIN_MMI = 1000


def to_ordered_dict(series):
    keys = series.index
    mydict = OrderedDict()

    np_int_types = (np.int8, np.int16, np.int32, np.int64,
                    np.uint8, np.uint16, np.uint32, np.uint64)
    np_float_types = (np.float32, np.float64)

    for key in keys:
        if isinstance(series[key], np_int_types):
            svalue = int(series[key])
        elif isinstance(series[key], np_float_types):
            svalue = float(series[key])
        else:
            svalue = series[key]
        mydict[key] = svalue
    return mydict


def _select_by_max_mmi(df, mmi, minimum=1000):
    mmi_indices = {1: 'MMI1', 2: 'MMI2', 3: 'MMI3', 4: 'MMI4',
                   5: 'MMI5', 6: 'MMI6', 7: 'MMI7', 8: 'MMI8', 9: 'MMI9+'}
    for idx in np.arange(mmi, 10):
        mmicol = mmi_indices[idx]
        anymmi = df[df[mmicol] >= minimum]
        return anymmi
    return None


class ExpoCat(object):
    def __init__(self, dataframe):
        """Create an ExpoCat object from a dataframe input.

        :param dataframe:
          Pandas dataframe containing columns:
            - EventID  14 character event ID based on time: (YYYYMMDDHHMMSS).
            - Time Pandas Timestamp object.
            - Name Name of earthquake (not always filled in).
            - Lat  Event latitude.
            - Lon  Event longitude.
            - Depth  Event depth.
            - Magnitude  Event magnitude.
            - CountryCode  Two letter country code in which epicenter is located.
            - ShakingDeaths Number of fatalities due to shaking.
            - TotalDeaths Number of total fatalities.
            - Injured Number of injured.
            - Fire Integer (0 or 1) indicating if any fires occurred as a result of this earthquake.
            - Liquefaction Integer (0 or 1) indicating if any liquefaction occurred as a result of this earthquake.
            - Tsunami Integer (0 or 1) indicating if any tsunamis occurred as a result of this earthquake.
            - Landslide Integer (0 or 1) indicating if any landslides occurred as a result of this earthquake.
            - MMI1 - Number of people exposed to Mercalli intensity 1.
            - MMI2 - Number of people exposed to Mercalli intensity 2.
            - MMI3 - Number of people exposed to Mercalli intensity 3.
            - MMI4 - Number of people exposed to Mercalli intensity 4.
            - MMI5 - Number of people exposed to Mercalli intensity 5.
            - MMI6 - Number of people exposed to Mercalli intensity 6.
            - MMI7 - Number of people exposed to Mercalli intensity 7.
            - MMI8 - Number of people exposed to Mercalli intensity 8.
            - MMI9+ Number of people exposed to Mercalli intensity 9 and above.
            - MaxMMI  Highest intensity level with at least 1000 people exposed.
            - NumMaxMMI Number of people exposed at MaxMMI.
        """
        self._dataframe = dataframe.copy()

    @classmethod
    def fromDefault(cls):
        """Read in data from Excel file included in the distribution of this code.

        :returns:
          ExpoCat object.
        """
        homedir = os.path.dirname(os.path.abspath(
            __file__))  # where is this module?
        excelfile = os.path.join(homedir, '..', 'data', 'expocat.xlsx')
        return cls.fromExcel(excelfile)

    @classmethod
    def fromExcel(cls, excelfile):
        """Read in data from Expocat CSV file.

        :param excelfile:
          Excel file containing columns as described above for constructor, minus the MaxMMI and NumMaxMMI columns.
        :returns:
          ExpoCat object.
        """
        df = pd.read_excel(excelfile,
                           converters={'EventID': str})

        #df = df.drop('Unnamed: 0',1)

        # cols = ['EventID','Time','Name','Lat','Lon','Depth','Magnitude','CountryCode',
        #         'ShakingDeaths','TotalDeaths','Injured','Fire','Liquefaction','Tsunami',
        #         'Landslide','Waveheight',
        #         'MMI1','MMI2','MMI3','MMI4','MMI5','MMI6','MMI7','MMI8','MMI9+',]
        # df = df[cols]

        mmicols = ['MMI1', 'MMI2', 'MMI3', 'MMI4',
                   'MMI5', 'MMI6', 'MMI7', 'MMI8', 'MMI9+']

        # find the highest MMI column in each row with at least 1000 people exposed.
        # mmidata = df.ix[:, mmicols].values
        mmidata = df[mmicols].values
        tf = mmidata > 1000
        nrows, ncols = mmidata.shape
        colmat = np.tile(np.arange(0, ncols), (nrows, 1))
        imax = np.argmax(colmat * tf, axis=1)
        nmaxmmi = np.diagonal(mmidata[:, imax])
        maxmmi = imax + 1

        df['MaxMMI'] = pd.Series(maxmmi)
        df['NumMaxMMI'] = pd.Series(nmaxmmi)

        return cls(df)

    @classmethod
    def fromCSV(cls, csvfile):
        """Read in data from Expocat CSV file.

        :param csvfile:
          CSV file containing columns as described above for constructor, minus the MaxMMI and NumMaxMMI columns.
        :returns:
          ExpoCat object.
        """
        df = pd.read_csv(csvfile, parse_dates=[1], dtype={'EventID': str})
        #df = df.drop('Unnamed: 0',1)

        cols = ['EventID', 'Time', 'Name', 'Lat', 'Lon', 'Depth', 'Magnitude', 'CountryCode',
                'ShakingDeaths', 'TotalDeaths', 'Injured', 'Fire', 'Liquefaction', 'Tsunami',
                'Landslide', 'Waveheight',
                'MMI1', 'MMI2', 'MMI3', 'MMI4', 'MMI5', 'MMI6', 'MMI7', 'MMI8', 'MMI9+', ]
        df = df[cols]

        mmicols = ['MMI1', 'MMI2', 'MMI3', 'MMI4',
                   'MMI5', 'MMI6', 'MMI7', 'MMI8', 'MMI9+']

        # find the highest MMI column in each row with at least 1000 people exposed.
        mmidata = df[mmicols].values
        tf = mmidata > 1000
        nrows, ncols = mmidata.shape
        colmat = np.tile(np.arange(0, ncols), (nrows, 1))
        imax = np.argmax(colmat * tf, axis=1)
        nmaxmmi = np.diagonal(mmidata[:, imax])
        maxmmi = imax + 1

        df['MaxMMI'] = pd.Series(maxmmi)
        df['NumMaxMMI'] = pd.Series(nmaxmmi)

        return cls(df)

    def __len__(self):
        """Return the number of rows in this object's dataframe.

        :returns:
          Number of rows in this object's dataframe.
        """
        return len(self._dataframe)

    def __add__(self, other):
        """Add two ExpoCat objects together by concatenating their internal dataframes.

        :param other:
          ExpoCat object.
        :returns:
          An ExpoCat object consisting of events from this ExpoCat object and those from other.
        """
        newdf = pd.concat(
            [self._dataframe, other._dataframe]).drop_duplicates()
        return ExpoCat(newdf)

    def excludeFutureEvents(self, event_time):
        """ Exclude events after given event_time from further searches.
        As some searches may be used for historical events, excluding events after a given time
        will be desired.

        :param event_time:
          datetime object representing most recent time desired for searches from within this object.
        """
        self._dataframe = self._dataframe[(
            self._dataframe['Time'] < event_time)]

    def getDataFrame(self):
        """Return a copy of the dataframe contained in this ExpoCat object.

        :returns:
          A copy of the dataframe contained in this ExpoCat object.
        """
        return self._dataframe.copy()

    def selectByHazard(self, hazard):
        """Select down the events in the ExpoCat by restricting to events with input hazard.

        :param hazard:
          String, one of 'fire','liquefaction','landslide', or 'tsunami'.
        :returns:
          List consisting of zero or more of the above hazard strings.
        :raises:
           PagerException when input hazard does not match one of the four accepted types.
        :returns:
          New instance of ExpoCat.
        """
        haztypes = ['fire', 'liquefaction', 'landslide', 'tsunami']
        if hazard not in haztypes:
            raise PagerException(
                'Input hazard %s not one of accepted hazard types: %s' % (hazard, str(haztypes)))
        colname = hazard.capitalize()
        newdf = self._dataframe[self._dataframe[colname] == 1]
        return ExpoCat(newdf)

    def selectByTime(self, mintime, maxtime):
        """Select down the events in the ExpoCat by restricting to events between two input times.

        :param mintime:
          Pandas Timestamp object OR Python datetime object.
        :param maxtime:
          Pandas Timestamp object OR Python datetime object.
        :returns:
          Reduced ExpoCat set of events to those inside the input time bounds.
        """
        if mintime >= maxtime:
            raise PagerException('Input mintime must be less than maxtime.')

        newdf = self._dataframe[(self._dataframe['Time'] > mintime) & (
            self._dataframe['Time'] <= maxtime)]
        return ExpoCat(newdf)

    def selectByMagnitude(self, minmag, maxmag=None):
        """Select down the events in the ExpoCat by restricting to events between two input magnitudes.

        :param minmag:
          Float earthquake minimum magnitude.
        :param maxmag:
          Float earthquake maximum magnitude.
        :returns:
          Reduced ExpoCat set of events to those inside the input magnitude bounds.
        """
        if maxmag is not None:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag) & (
                self._dataframe['Magnitude'] <= maxmag)]
        else:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag)]
        return ExpoCat(newdf)

    def selectByBounds(self, xmin, xmax, ymin, ymax):
        """Select down the events in the ExpoCat by restricting to events inside bounding box.

        :param xmin:
          Minimum longitude.
        :param xmax:
          Maximum longitude.
        :param ymin:
          Minimum latitude.
        :param ymax:
          Maximum latitude.
        :returns:
          Reduced ExpoCat set of events to those inside bounding box.
        """
        idx1 = (self._dataframe['Lat'] > ymin)
        idx2 = (self._dataframe['Lat'] <= ymax)
        idx3 = (self._dataframe['Lon'] > xmin)
        idx4 = (self._dataframe['Lon'] <= xmax)
        newdf = self._dataframe[idx1 & idx2 & idx3 & idx4]
        return ExpoCat(newdf)

    def selectByShakingDeaths(self, mindeaths):
        """Select down the events in the ExpoCat by restricting to events with shaking deaths greater than input.

        :param mindeaths:
          Minimum shaking fatality threshold.
        :returns:
          Reduced ExpoCat set of events to those with shaking fatalities greater than mindeaths.
        """
        newdf = self._dataframe[self._dataframe['ShakingDeaths'] >= mindeaths]
        return ExpoCat(newdf)

    def selectByRadius(self, clat, clon, radius):
        """Select events by restricting to those within a search radius around a set of coordinates.

        """
        lons = self._dataframe['Lon']
        lats = self._dataframe['Lat']
        distances = geodetic_distance(clon, clat, lons, lats)
        iclose = pd.Series(distances < radius)
        newdf = self._dataframe[iclose]
        d1 = distances[distances < radius]
        newdf = newdf.assign(Distance=d1)
        return ExpoCat(newdf)

    def getHistoricalEvents(self, maxmmi, nmmi, ndeaths, clat, clon):
        """Select three earthquakes from internal list that are "representative" and similar to input event.

        First event should be the event "most similar" in exposure, and with the fewest fatalities.
        Second event should also be "similar" in exposure, and with the most fatalities.
        Third event should be the deadliest and/or highest population exposure event.

        :param maxmmi:
          MMI level of maximum exposure.
        :param nmmi:
          Number of people exposure to maxmmi.
        :param ndeaths:
          Number of estimated people killed from shaking.
        :param clat:
          Origin latitude.
        :param clon:
          Origin latitude.
        :returns:
          List of three dictionaries (or three None values), containing fields:
            - EventID  14 character event ID based on time: (YYYYMMDDHHMMSS).
            - Time Pandas Timestamp object.
            - Lat  Event latitude.
            - Lon  Event longitude.
            - Depth  Event depth.
            - Magnitude  Event magnitude.
            - CountryCode  Two letter country code in which epicenter is located.
            - ShakingDeaths Number of fatalities due to shaking.
            - TotalDeaths Number of total fatalities.
            - Injured Number of injured.
            - Fire Integer (0 or 1) indicating if any fires occurred as a result of this earthquake.
            - Liquefaction Integer (0 or 1) indicating if any liquefaction occurred as a result of this earthquake.
            - Tsunami Integer (0 or 1) indicating if any tsunamis occurred as a result of this earthquake.
            - Landslide Integer (0 or 1) indicating if any landslides occurred as a result of this earthquake.
            - MMI1 - Number of people exposed to Mercalli intensity 1.
            - MMI2 - Number of people exposed to Mercalli intensity 2.
            - MMI3 - Number of people exposed to Mercalli intensity 3.
            - MMI4 - Number of people exposed to Mercalli intensity 4.
            - MMI5 - Number of people exposed to Mercalli intensity 5.
            - MMI6 - Number of people exposed to Mercalli intensity 6.
            - MMI7 - Number of people exposed to Mercalli intensity 7.
            - MMI8 - Number of people exposed to Mercalli intensity 8.
            - MMI9+ Number of people exposed to Mercalli intensity 9 and above.
            - MaxMMI  Highest intensity level with at least 1000 people exposed.
            - NumMaxMMI Number of people exposed at MaxMMI.
            - Distance Distance of this event from input event, in km.
            - Color The hex color that should be used for row color in historical events table.
        """
        # get the worst event first
        newdf = self._dataframe.sort_values(
            ['ShakingDeaths', 'MaxMMI', 'NumMaxMMI'], ascending=False)
        if not len(newdf):
            return [None, None, None]
        worst = newdf.iloc[0]
        # get rid of that first row, so we don't re-include the same event
        newdf = newdf.drop(newdf.index[[0]])
        if not len(newdf):
            less_bad = None
        else:  # get the similar but less bad event
            less_bad, newdf = self.getSimilarEvent(
                newdf, maxmmi, nmmi, ndeaths, go_down=True)

        if not len(newdf):
            more_bad = None
        else:  # get the similar but worse event
            more_bad, newdf = self.getSimilarEvent(
                newdf, maxmmi, nmmi, ndeaths, go_down=False)

        events = []
        colormap = ColorPalette.fromPreset('mmi')
        if less_bad is not None:
            lessdict = to_ordered_dict(less_bad)
            rgbval = colormap.getDataColor(lessdict['MaxMMI'])
            rgb255 = tuple([int(c * 255) for c in rgbval])[0:3]
            lessdict['Color'] = '#%02x%02x%02x' % rgb255
            events.append(lessdict)

        if more_bad is not None:
            moredict = to_ordered_dict(more_bad)
            rgbval = colormap.getDataColor(moredict['MaxMMI'])
            rgb255 = tuple([int(c * 255) for c in rgbval])[0:3]
            moredict['Color'] = '#%02x%02x%02x' % rgb255
            events.append(moredict)

        worstdict = to_ordered_dict(worst)
        rgbval = colormap.getDataColor(worstdict['MaxMMI'])
        rgb255 = tuple([int(c * 255) for c in rgbval])[0:3]
        worstdict['Color'] = '#%02x%02x%02x' % rgb255
        events.append(worstdict)

        return events

    def getSimilarEvent(self, df, maxmmi, nmmi, ndeaths, go_down=True):
        # Algorithm description: if go_down == True
        # 1)find any events in df where maxmmi == input maxmmi and deaths > ndeaths.
        # if there are any of these, find the event where deaths is closest to ndeaths and return.
        # 2)while maxmmi >= 1, decrement maxmmi and find any events in df where maxmmi == new maxmmi
        # and deaths > ndeaths.  If any, find event where deaths is closest to ndeaths and return.
        # 3)while maxmmi <= 9, increment maxmmi and find any events in df where maxmmi == new maxmmi
        # and deaths > ndeaths.  If any, find event where deaths is closest to ndeaths and return.
        # 4)Sort df by shaking fatalities, maxmmi and nmmi in descending order.  Return the first event.

        # if go_down == False
        # do the same thing as above except #2 increment maxmmi and #3 decrement maxmmi.

        # get all of the events with the same maxmmi as input
        newdf = df[df.MaxMMI == maxmmi]

        # if we're searching for the most similar but less bad event, go_down is True
        newmaxmmi = maxmmi
        if go_down:
            mmi1 = 0
            mmi2 = 10
            inc1 = -1
            inc2 = 1
            ascending = True
        else:
            mmi1 = 10
            mmi2 = 0
            inc1 = 1
            inc2 = -1
            ascending = False

        # if go_down is True, we're going down here (up if not)
        for newmaxmmi in range(maxmmi, mmi1, inc1):
            newdf = df[(df.MaxMMI == newmaxmmi) & (df.ShakingDeaths > ndeaths)]
            if len(newdf):
                ismall = ((newdf.ShakingDeaths - ndeaths).abs()
                          ).values.argmin()
                similar = newdf.iloc[ismall]
                newdf = df.drop(similar.name)
                return (similar, newdf)

        # if go_down is True, we're going up here (down if not)
        for newmaxmmi in range(maxmmi, mmi2, inc2):
            newdf = df[(df.MaxMMI == newmaxmmi) & (df.ShakingDeaths > ndeaths)]
            if len(newdf):
                ismall = ((newdf.ShakingDeaths - ndeaths).abs()
                          ).values.argmin()
                similar = newdf.iloc[ismall]
                newdf = df.drop(similar.name)
                return (similar, newdf)

        newdf = df.sort_values(
            ['ShakingDeaths', 'MaxMMI', 'NumMaxMMI'], ascending=ascending)
        similar = newdf.iloc[0]
        newdf = df.drop(similar.name)
        return (similar, newdf)

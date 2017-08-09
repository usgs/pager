#!/usr/bin/env python

#third party imports
import pandas as pd
from mapio.grid2d import Grid2D
import numpy as np

#stdlib imports
import re
import os.path

#local imports
from .exposure import Exposure
from .emploss import EmpiricalLoss
from .growth import PopulationGrowth
from losspager.utils.country import Country

GLOBAL_GDP = 16100 #from https://en.wikipedia.org/wiki/Gross_world_product

class GDP(object):
    def __init__(self, dataframe):
        """Create an instance of a GDP object with a dataframe of countries/GDP values over time.
        
        :param dataframe:
          Pandas dataframe where rows are countries, and columns are rates for different years.
          dataframe should look like this:
          DataFrame({'Country Code':['AFG'],
                     '1960':[59.78768071],
                     '1961':[59.89003694],})
          The above contains the GDP values for Afghanistan for 1960 and 196
        """
        self._dataframe = dataframe
        self._country = Country()

    @classmethod
    def fromDefault(cls):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this module?
        excelfile = os.path.join(homedir, '..', 'data', 'API_NY.GDP.PCAP.CD_DS2_en_excel_v2.xls')
        return cls.fromWorldBank(excelfile)
        
    @classmethod
    def fromWorldBank(cls, excelfile):
        """Read in Excel data from the World Bank containing per capita GDP values for all countries in the world.
        Taken from: http://data.worldbank.org/indicator/NY.GDP.PCAP.CD
        
        :param excelfile:
          Excel spreadsheet downloaded from above source.
        :returns:
          GDP instance.
        """
        df = pd.read_excel(excelfile, sheetname='Data', header=3)
        return cls(df)

    def getGDP(self, ccode, year):
        """Get the GDP value for a given country code and a particular year.

        :param ccode:
          Any of ISO2, ISO3, or ISON country codes.
        :param year:
          Year of desired GDP value.  If this year is before the earliest year in the data source, 
          the earliest GDP value will be used. If this year is after the latest year in the data source, 
          the latest non-NaN GDP value will be used.
        :returns:
          Tuple of: 
            - GDP value corresponding to country code and year, unless country code is not found, in which case
            a default global GDP value will be returned.
            - The country code which is most applicable to the output GDP.  For example, if the GDP value chosen 
              is the global value, then this country code will be None.  If the input country code is XF (California),
              then the output country code will be 'US'.
        """
        #first make sure the ccode is valid...
        countrydict = self._country.getCountry(ccode)
        if countrydict is None:
            return (GLOBAL_GDP, None)
        if countrydict['ISO2'] in ['XF', 'EU', 'WU']:
            ccode = 'USA'
            outccode = 'US'
        else:
            ccode = countrydict['ISO3']
            outccode = ccode
        yearstr = str(year)
        try:
            row = self._dataframe[self._dataframe['Country Code'] == ccode].iloc[0]
        except:
            return (GLOBAL_GDP, None)
        
        if yearstr in row:
            gdp = row[yearstr]
        else:
            row = row.dropna()
            columns = row.index.tolist()
            years = []
            for c in columns:
                res = re.search('[0-9]{4}', c)
                if res is not None:
                    years.append(res.group())

            if not len(years):
                return (GLOBAL_GDP, None)
            if yearstr < min(years):
                #assume that the years in the dataframe are sequential and increasing to the right
                #get the first non-null GDP value
                if pd.isnull(row[min(years)]):
                    gdp = GLOBAL_GDP
                else:
                    gdp = row[min(years)]
            else:
                #get the last non-null GDP value
                if pd.isnull(row[max(years)]):
                    gdp = GLOBAL_GDP
                else:
                    gdp = row[max(years)]

        return (gdp, outccode)
        

class EconExposure(Exposure):
    def __init__(self, popfile, popyear, isofile):
        """Create instance of EconExposure class (subclass of Exposure, and shares methods of that class.)

        :param popfile:
          Any GMT or ESRI style grid file supported by MapIO, containing population data.
        :param popyear:
          Integer indicating year when population data is valid.
        :param isofile:
          Any GMT or ESRI style grid file supported by MapIO, containing country code data (ISO 3166-1 numeric).
        """
        self._emploss = EmpiricalLoss.fromDefaultEconomic()
        self._gdp = GDP.fromDefault()
        self._econpopgrid = None
        popgrowth = PopulationGrowth.fromDefault()
        super(EconExposure, self).__init__(popfile, popyear, isofile)

    def getEconPopulationGrid(self):
        """Return the internal economic exposure population grid, created during calcExposure().

        :raises:
          PagerException when calcExposure() has not been called.
        """
        if self._econpopgrid is None:
            raise PagerException('Must call calcExposure() before calling getEconPopulationGrid().')
        return self._econpopgrid
        
    def calcExposure(self, shakefile):
        """Calculate population exposure to shaking.

        Calculate population exposure to shaking, per country, multiplied by event-year per-capita GDP and 
        alpha correction factor.  Also multiply the internal population grid by GDP and 
        alpha.

        :param shakefile:
          Path to ShakeMap grid.xml file.
        :returns:
          Dictionary containing country code (ISO2) keys, and values of
          10 element arrays representing population exposure to MMI 1-10.
          Dictionary will contain an additional key 'Total', with value of exposure across all countries.
        """
        #create a copy of population grid to hold population * gdp * alpha
        expdict = super(EconExposure, self).calcExposure(shakefile)
        self._econpopgrid = Grid2D.copyFromGrid(self._popgrid)
        econdict = {}
        isodata = self._isogrid.getData()
        eventyear = self.getShakeGrid().getEventDict()['event_timestamp'].year
        total = np.zeros((10,))
        for ccode, exparray in expdict.items():
            if ccode.find('Total') > -1 or ccode.find('maximum') > -1:
                continue
            if ccode == 'UK': #unknown
                continue
            lossmodel = self._emploss.getModel(ccode)
            gdp, outccode = self._gdp.getGDP(ccode, eventyear)
            isocode = self._country.getCountry(ccode)['ISON']
            alpha = lossmodel.alpha
            econarray = exparray * gdp * alpha
            cidx = (isodata == isocode)
            #multiply the population grid by GDP and alpha, so that when the loss model
            #queries the grid later, those calculations don't have to be re-done.
            self._econpopgrid._data[cidx] = self._econpopgrid._data[cidx] * gdp * alpha
            econdict[ccode] = econarray
            total += econarray

        econdict['TotalEconomicExposure'] = total
        return econdict
    

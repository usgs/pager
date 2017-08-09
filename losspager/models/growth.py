#!/usr/bin/env python

#stdlib imports
import re
import os.path

#third party imports
import pandas as pd
import numpy as np

#local imports
from losspager.utils.exception import PagerException
from losspager.utils.country import Country

DEFAULT_RATE = 1.17/100.0

def adjust_pop(population, tpop, tevent, rate):
    """Adjust input population between two input years given growth rate.

    :param population:
      Population starting value at time *tpop*.
    :param tpop:
      Year in which input population data was collected.
    :param tevent:
      Year to which population data should be adjusted.
    :param rate:
      Population growth rate value.
    :returns:
      Adjusted population value at time *tevent*.
    """
    T = tpop - tevent
    adjpop = np.round(population * np.power((1 + rate), (-1*T)))
    return adjpop

class PopulationGrowth(object):
    def __init__(self, ratedict, default_rate=DEFAULT_RATE):
        """Initialize Population growth with dictionary containing rates over given time 
        spans, per country.  

        :param ratedict:
          dictionary like: {841: {'end': [1955, 1960, 1965],
                                  'rate': [0.01, 0.02, 0.03],
                                  'start': [1950, 1955, 1960]},
                            124: {'end': [1955, 1960, 1965],
                                  'rate': [0.02, 0.03, 0.04],
                                  'start': [1950, 1955, 1960]}}
          Where 841 and 842 in this case are country codes (US and Canada), and the three "columns" for each 
          country are the year start of each time interval, the year end of each time interval, and the growth 
          rates for those time intervals.
        :param default_rate:
          Value to be used for growth rate when input country codes are not found in ratedict.
        """
        #check the fields in the ratedict
        for key, value in ratedict.items():
            if 'start' not in value or 'end' not in value or 'rate' not in value:
                raise PagerException('All country rate dictionaries must contain keys "start","end","rate"')
            if not (len(value['start']) == len(value['end']) == len(value['rate'])):
                raise PagerException('Length of start/end year arrays must match length of rate arrays.')
        self._dataframe = pd.DataFrame(ratedict)
        self._default = default_rate


    @classmethod
    def fromDefault(cls):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this module?
        excelfile = os.path.join(homedir, '..', 'data', 'WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
        return cls.fromUNSpreadsheet(excelfile)
        
    @classmethod
    def fromUNSpreadsheet(cls, excelfile, default_rate=DEFAULT_RATE):
        """Instantiate population growth rates from UN global spreadsheet.
        http://esa.un.org/unpd/wpp/Download/Standard/Population/

        :param excelfile:
          Path to Excel file containing UN population growth rate data per country.
        :param default_rate:
          Value to be used for growth rate when input country codes are not found in ratedict.
        :returns:
          PopulationGrowth instance.
        """
        re_year = '[0-9]*'
        df = pd.read_excel(excelfile, header=16)
        ratedict = {}
        starts = []
        ends = []
        for col in df.columns:
            matches = re.findall(re_year, col)
            if len(matches) and len(matches[0]):
                starts.append(int(matches[0]))
                ends.append(int(matches[2]))

        ccode_idx = df.columns.get_loc('Country code')
        uscode = 840
        usrates = None
        country = Country()
        for idx, row in df.iterrows():
            key = row['Country code']
            rates = row.iloc[ccode_idx+1:].as_matrix()/100.0
            if key == uscode:
                usrates = rates.copy()
            if country.getCountry(key) is None:
                continue
            ratedict[key] = {'start': starts[:], 'end': ends[:], 'rate': rates}

        #we have three non-standard "country" codes for California, eastern US, and western US.
        ratedict[902] = {'start': starts[:], 'end': ends[:], 'rate': usrates}
        ratedict[903] = {'start': starts[:], 'end': ends[:], 'rate': usrates}
        ratedict[904] = {'start': starts[:], 'end': ends[:], 'rate': usrates}
            
        return cls(ratedict, default_rate=default_rate)

    def getRate(self, ccode, year):
        """Return population growth rate(s) for a given country code and year.

        :param ccode:
          Numeric country code.
        :param year:
          Integer year to be used to find growth rate (will be between start and end years,
          or before first start year or after last end year).
        :returns:
          Scalar growth rate.
        """
        if ccode not in self._dataframe.columns:
            return self._default
        starts = np.array(self._dataframe[ccode]['start'])
        ends = np.array(self._dataframe[ccode]['end'])
        rates = np.array(self._dataframe[ccode]['rate'])
        if year is None:
            return dict(list(zip(starts, rates)))
        if year < starts.min():
            rate = rates[0]
        elif year > ends.max():
            rate = rates[-1]
        else:
            idx = (np.abs(year-ends)).argmin()
            rate = rates[idx]
        return rate

    def getRates(self, ccode):
        """Return population growth rates for a given country code.

        :param ccode:
          Numeric country code.
        :param year:
          Integer year to be used to find growth rate (will be between start and end years,
          or before first start year or after last end year).
        :returns:
          Tuple of two lists of (start_years,rates).
        """
        if ccode not in self._dataframe.columns:
            raise PagerException('Country %s not found in PopulationGrowth data structure.' % ccode)
        starts = np.array(self._dataframe[ccode]['start'])
        rates = np.array(self._dataframe[ccode]['rate'])
        return (starts, rates)

    def adjustPopulation(self, population, ccode, tpop, tevent):
        """Adjust population based on growth rates.

        :param population:
          Number of people.
        :param ccode:
          Numeric country code.
        :param tpop:
          Year of population data collection.
        :param tevent:
          Year to which population data should be adjusted from tpop.
        :returns:
          Population adjusted for growth rates in years between tpop and tevent. 
        """
        if tpop == tevent:
            return population
        if tpop < tevent:
            interval = 1
        else:
            interval = -1
        newpop = population
        for startpop in np.arange(tpop, tevent, interval):
            endpop = startpop + interval
            rate = self.getRate(ccode, startpop)
            newpop = adjust_pop(newpop, startpop, endpop, rate)

        return newpop
        
        
    
    

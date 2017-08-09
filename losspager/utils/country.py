#!/usr/bin/env python

#stdlib imports
import os.path

#third party imports
import pandas as pd

class Country(object):
    def __init__(self):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
        excelfile = os.path.abspath(os.path.join(homedir, '..', 'data', 'countries.xlsx'))
        self._loadFromExcel(excelfile)        
    
    def getUSCode(self, code):
        """Handle US-region specific codes for California, Eastern US, and Western US.

        :param code:
          Input numeric country code.
        :returns:
          840 if input is in (902,903,904), input ccode otherwise.
        """
        if code in (902, 903, 904):
            return 840
        else:
            return code

    def _loadFromExcel(self, excelfile):
        self._dataframe = pd.read_excel(excelfile)
        idx = pd.isnull(self._dataframe['Name'])
        self._dataframe.loc[idx, 'Name'] = self._dataframe['LongName'][idx]
        
    def _loadFromCSV(self, csvfile):
        """Load from a CSV file containing five columns: LongName,ISO2,ISO3,ISON,Name.

        NB: 

          There are three PAGER-specific country codes in the PAGER countries.csv file.
          - 902: California
          - 903: Eastern US
          - 904: Western US
        
        :param csvfile:
          CSV file containing country information with the following columns:
           - LongName: Long country name.
           - ISO2: Two letter country code.
           - ISO3: Three letter country code.
           - ISON: Numeric country code.
           - Name: Short country name.
           - Source: https://en.wikipedia.org/wiki/ISO_3166-1
        
        """
        self._dataframe = pd.read_csv(csvfile)
        cols = ['LongName', 'ISO2', 'ISO3', 'ISON', 'Name']
        for col in cols:
            if col not in self._dataframe.columns:
                raise PagerException('PAGER country CSV file must contain columns: %s.' % str(cols))

        idx = pd.isnull(self._dataframe['Name'])
        self._dataframe.loc[idx, 'Name'] = self._dataframe['LongName'][idx]

    def getCountry(self, value):
        """Return a dictionary containing the country name/codes for the first country that matches the input value.

        N.B. 

          This method matches the first country it can, which means that in the case of an input "guinea", for
          example, you would get back the data for "Equatorial Guinea", as opposed to "Guinea", "Guinea-Bissau", or 
          "Papua New Guinea".  Also be aware that there is a country code for "United States Minor Outlying Islands".
        
        :param value:
          One of: 
           - Two letter ISO 3166 country code (JP,US, etc.)
           - Three letter ISO 3166 country code (JPN,USA, etc.)
           - Numerical ISO 3166 country code (392,840, etc.)
           - Name or name fragment (Japan,united states of america, etc.)
           
        :returns:
          Dictionary containing the following:
            - Name: Short name (i.e., Bolivia)
            - LongName: Long name (i.e., Plurinational State of Bolivia)
            - ISO2: Two letter ISO country code (BO)
            - ISO3: Two letter ISO country code (BOL)
            - ISON: Numeric ISO country code (68)
            - Population Number of people inside the country.
          or None if the input value does not match any known country data.
        
        """
        emptyrow = {'Name': 'Unknown',
               'LongName': 'Unknown',
               'ISO2': 'UK',
               'ISO3': 'UKN',
               'ISON': 0,
               'Population': 0}
        row = None
        if isinstance(value, (int, float)):
            row = self._dataframe[self._dataframe['ISON'] == value]
        elif isinstance(value, str):
            if len(value) == 0:
                return emptyrow
            if len(value) == 2:
                row = self._dataframe[self._dataframe['ISO2'] == value]
            elif len(value) == 3:
                row = self._dataframe[self._dataframe['ISO3'] == value]
            else:
                row = self._dataframe[self._dataframe.Name.str.lower().str.contains(value.lower())]
        if row is None:
            return emptyrow
        else:
            if len(row) > 0:
                return row.iloc[0].to_dict()
            elif not len(row):
                return emptyrow
            else:
                return row.to_dict()
                

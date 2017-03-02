#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np

#local imports
from losspager.utils.country import Country

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    countryfile = os.path.abspath(os.path.join(homedir,'..','..','data','countries.csv'))
    testdict = {'ISON': 840, 'ISO3': 'USA', 
                'ISO2': 'US', 'LongName': 'United States', 
                'Name': 'United States', 'Population': 324515000}

    print('Test creating Country object from CSV file...')
    country = Country()
    print('Passed creating Country object from CSV file.')

    print('Test retrieving dictionary from two letter code...')
    row1 = country.getCountry('US')
    assert row1 == testdict
    print('Passed retrieving dictionary from two letter code...')

    print('Test retrieving dictionary from three letter code...')
    row2 = country.getCountry('USA')
    assert row2 == testdict
    print('Passed retrieving dictionary from three letter code...')

    print('Test retrieving dictionary from name...')
    row3 = country.getCountry('United States')
    assert row3 == testdict
    print('Passed retrieving dictionary from name.')

    print('Test retrieving dictionary from numeric code...')
    row4 = country.getCountry(840)
    assert row4 == testdict
    print('Passed retrieving dictionary from numeric code...')

    print('Test to make sure failure is an option...')
    faildict = {'Name':'Unknown',
                'LongName':'Unknown',
                'ISO2':'UK',
                'ISO3':'UKN',
                'ISON':0,
                'Population':0}
    row5 = country.getCountry('happyland')
    assert row5 == faildict
    print('Test failed as expected...')


if __name__ == '__main__':
    test()

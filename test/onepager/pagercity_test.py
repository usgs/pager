#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys
from datetime import datetime

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir, '..', '..'))
sys.path.insert(0, pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
from mapio.basemapcity import BasemapCities
from mapio.city import Cities
from mapio.shake import ShakeGrid

#local imports
from losspager.onepager.pagercity import PagerCities

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    cityfile = os.path.join(homedir, '..', 'data', 'cities1000.txt')
    shakefile1 = os.path.join(homedir, '..', 'data', 'eventdata', 'northridge', 'northridge_grid.xml')
    shakefile2 = os.path.join(homedir, '..', 'data', 'eventdata', 'lomaprieta', 'lomaprieta_grid.xml')
    shakefiles = [shakefile1, shakefile2]
    lengths = [11, 11]
    first_city = ['Santa Clarita', 'Lexington Hills']
    last_city = ['Bakersfield', 'Fresno']
    ic = 0
    cities = Cities.loadFromGeoNames(cityfile)
    for shakefile in shakefiles:
        shakemap = ShakeGrid.load(shakefile, adjust='res')

        #get the top ten (by population) nearby cities
        clat = shakemap.getEventDict()['lat']
        clon = shakemap.getEventDict()['lon']
        nearcities = cities.limitByRadius(clat, clon, 100)
        nearcities.sortByColumns('pop', ascending=False)
        nearcities = Cities(nearcities._dataframe.iloc[0:10])
        mmigrid = shakemap.getLayer('mmi')
        pc = PagerCities(cities, mmigrid)
        rows = pc.getCityTable(nearcities)
        print('Testing that number of cities retrieved is consistent...')
        assert len(rows) == lengths[ic]
        assert rows.iloc[0]['name'] == first_city[ic]
        assert rows.iloc[-1]['name'] == last_city[ic]
        print('Passed.')
        ic += 1
    
if __name__ == '__main__':
    test()

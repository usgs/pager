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
sys.path.insert(0, pagerdir) #put this at the front of the system path, ignoring any installed pager stuff

#third party imports 
import numpy as np

#local imports
from losspager.utils.expocat import ExpoCat

def commify(value):
    if np.isnan(value):
        return 'NaN'
    return format(int(value), ",d")

def get_max_mmi(tdict, minimum=1000):
    indices = ['MMI1', 'MMI2', 'MMI3', 'MMI4', 'MMI5', 'MMI6', 'MMI7', 'MMI8', 'MMI9+']
    exparray = np.array([tdict[idx] for idx in indices])
    imax = (exparray > 1000).nonzero()[0].max()
    return (imax+1, exparray[imax])

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    expocat = ExpoCat.fromDefault()
    clat = 0.37
    clon = -79.94
    radius = 400
    ndeaths = 9
    minicat = expocat.selectByRadius(clat, clon, radius)
    
    print('Testing that historical events returned are correct...')
    maxmmi = 8
    nmaxmmi = 103000
    events = minicat.getHistoricalEvents(maxmmi, nmaxmmi, ndeaths, clat, clon)
    assert events[0]['EventID'] == '199603282303'
    assert events[1]['EventID'] == '197912120759'
    assert events[2]['EventID'] == '198703060410'
    print('Passed.')

    print('Testing that events selected by hazard are correct...')

    fire = expocat.selectByHazard('fire')
    tsunami = expocat.selectByHazard('tsunami')
    liquefaction = expocat.selectByHazard('liquefaction')
    landslide = expocat.selectByHazard('landslide')
    
    assert fire._dataframe['Fire'].sum() == len(fire)
    assert tsunami._dataframe['Tsunami'].sum() == len(tsunami)
    assert liquefaction._dataframe['Liquefaction'].sum() == len(liquefaction)
    assert landslide._dataframe['Landslide'].sum() == len(landslide)

    #test exclusion method
    test_time = datetime(1994, 1, 1)
    expocat.excludeFutureEvents(test_time)
    assert expocat._dataframe['Time'].max() < test_time
    
    print('Passed.')
    
    
if __name__ == '__main__':
    test()

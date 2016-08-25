#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys
from datetime import datetime

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed pager stuff

#third party imports 
import numpy as np

#local imports
from losspager.utils.expocat import ExpoCat

def commify(value):
    if np.isnan(value):
        return 'NaN'
    return format(int(value),",d")

def get_max_mmi(tdict,minimum=1000):
    indices = ['MMI1','MMI2','MMI3','MMI4','MMI5','MMI6','MMI7','MMI8','MMI9+']
    exparray = np.array([tdict[idx] for idx in indices])
    imax = (exparray > 1000).nonzero()[0].max()
    return (imax+1,exparray[imax])

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    catfile = os.path.join(homedir,'..','data','expocat.csv')
    expocat = ExpoCat.loadFromCSV(catfile)
    start = datetime(2011,1,1,0,0,0)
    finish = datetime(2011,1,31,23,59,59)
    jan2012 = expocat.selectByTime(start,finish).getDataFrame()
    assert len(jan2012) == 9

    #test selectByMaxMMI
    #how many events have 1000+ people at MMI9?
    expevents = expocat.selectByMaxMMI(9,minimum=1000)
    nevents = len(expevents)
    assert nevents == 45
    
    width = 5.0
    # clat,clon = -36.911687, -72.841387
    # chile = expocat.selectByBounds(clon-width,clon+width,clat-width,clat+width)
    # high = chile.selectSimilarByExposure(8,22000,100,search='high')
    # low = chile.selectSimilarByExposure(8,22000,100,search='low',avoid_ids=[high['EventID']])
    # print(high)
    # print()
    # print(low)

    #get all events with 100 or more fatalities, then shuffle them
    bigdead = expocat.selectByShakingDeaths(100).getDataFrame().sample(frac=1)
    bigdead2 = bigdead.iloc[0:10] #this should be a random sample now
    for idx,event in bigdead2.iterrows():
        deaths = int(event['ShakingDeaths'])
        clat = event['Lat']
        clon = event['Lon']
        emag = event['Magnitude']
        etime = event['Time']
        maxmmi,nmmi = get_max_mmi(event.to_dict())
        inbounds = expocat.selectByBounds(clon-width,clon+width,clat-width,clat+width)
        high = inbounds.selectSimilarByExposure(maxmmi,nmmi,deaths,search='high',time=etime)
        if high is not None:
            low = inbounds.selectSimilarByExposure(maxmmi,nmmi,deaths,search='low',time=etime,avoid_ids=[high['EventID']])
        else:
            low = inbounds.selectSimilarByExposure(maxmmi,nmmi,deaths,search='low',time=etime)
        print('%19s %3s %9s %10s %10s %10s' % ('Event Time','Mag','Deaths','MMI7','MMI8','MMI9+'))
        dstr = commify(deaths)
        mmi7 = commify(event['MMI7'])
        mmi8 = commify(event['MMI8'])
        mmi9 = commify(event['MMI9+'])
        print('%19s %3.1f %9s %10s %10s %10s' % (str(etime),emag,dstr,mmi7,mmi8,mmi9))
        if high is not None:
            dstr = commify(high['ShakingDeaths'])
            mmi7 = commify(high['MMI7'])
            mmi8 = commify(high['MMI8'])
            mmi9 = commify(high['MMI9+'])
            print('%19s %3.1f %9s %10s %10s %10s - HIGH' % (str(high['Time']),high['Magnitude'],dstr,mmi7,mmi8,mmi9))
        else:
            print('None')
        if low is not None:
            dstr = commify(low['ShakingDeaths'])
            mmi7 = commify(low['MMI7'])
            mmi8 = commify(low['MMI8'])
            mmi9 = commify(low['MMI9+'])
            print('%19s %3.1f %9s %10s %10s %10s - LOW' % (str(low['Time']),low['Magnitude'],dstr,mmi7,mmi8,mmi9))
        else:
            print('None')
        print()
              
    
    
    
if __name__ == '__main__':
    test()

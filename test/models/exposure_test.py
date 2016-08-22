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
from losspager.models.exposure import Exposure,calc_exposure
from losspager.models.growth import PopulationGrowth

def basic_test():
    print('Testing very basic exposure calculation...')
    mmidata = np.array([[7,8,8,8,7],
                        [8,9,9,9,8],
                        [8,9,10,9,8],
                        [8,9,9,8,8],
                        [7,8,8,6,5]],dtype=np.float32)
    popdata = np.ones_like(mmidata)*1e7
    isodata = np.array([[4,4,4,4,4],
                        [4,4,4,4,4],
                        [4,4,156,156,156],
                        [156,156,156,156,156],
                        [156,156,156,156,156]],dtype=np.int32)    
    expdict = calc_exposure(mmidata,popdata,isodata)
    testdict = {4:np.array([0,0,0,0,0,0,2e7,6e7,4e7,0]),
                156:np.array([0,0,0,0,1e7,1e7,1e7,6e7,3e7,1e7])}

    for ccode,value in expdict.items():
        testvalue = testdict[ccode]
        np.testing.assert_almost_equal(value,testvalue)

    print('Passed very basic exposure calculation...')

def test():
    print('Testing Northridge exposure check (with GPW data).')
    events = ['northridge']
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    excelfile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    for event in events:
        shakefile = os.path.join(homedir,'..','data','eventdata',event,'%s_grid.xml' % event)
        popfile = os.path.join(homedir,'..','data','eventdata',event,'%s_gpw.flt' % event)
        isofile = os.path.join(homedir,'..','data','eventdata',event,'%s_isogrid.bil' % event)
    
        growth = PopulationGrowth.loadFromUNSpreadsheet(excelfile)
        exp = Exposure(popfile,2012,isofile,growth)
        results = exp.calcExposure(shakefile)
        cmpexposure = [0,0,1817,1767260,5840985,5780298,2738374,1559657,4094,0]
        np.testing.assert_almost_equal(cmpexposure,results['TotalExposure'])
    print('Passed Northridge exposure check (with GPW data).')
        


if __name__ == '__main__':
    basic_test()
    test()

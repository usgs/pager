#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys
from datetime import datetime
from collections import OrderedDict

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
from mapio.gmt import GMTGrid
from mapio.geodict import GeoDict
from mapio.shake import ShakeGrid

#local imports
from losspager.models.semimodel import get_time_of_day,pop_dist,SemiEmpiricalFatality,URBAN,RURAL,make_test_semi_model

def time_tests():
    tday,year,hour = get_time_of_day(datetime(2016,6,3,16,39,0),-117.6981)
    assert tday == 'transit'
    assert year == 2016
    assert hour == 8

    tday,year,hour = get_time_of_day(datetime(2016,6,3,19,39,0),-117.6981)
    assert tday == 'day'
    assert year == 2016
    assert hour == 11

    tday,year,hour = get_time_of_day(datetime(2016,6,4,7,39,0),-117.6981)
    assert tday == 'night'
    assert year == 2016
    assert hour == 23

    tday,year,hour = get_time_of_day(datetime(2017,1,1,1,0,0),-117.6981)
    assert tday == 'transit'
    assert year == 2016
    assert hour == 17

def work_tests():
    popi = 2000
    fwf = 0.5
    f_ind = 0.25
    fser = 0.25
    fagr = 0.5
    timeofday = 'day'
    dclass = URBAN
    res,nonres,outdoor = pop_dist(popi,fwf,f_ind,fser,fagr,timeofday,dclass)
    np.testing.assert_almost_equal(res,410)
    np.testing.assert_almost_equal(nonres,865)
    np.testing.assert_almost_equal(outdoor,725)

def model_test_simple():
    A = 4 #ccode for afghanistan
    J = 392 #ccode for japan
    R = 1 #rural code
    U = 2 #urban code
    #create a 5x5 population data set with 1000 people in each cell
    popdata = np.ones((5,5))*1000.0
    #create a mixed grid of afghanistan and japan (have very different inventory,collapse, and fatality rates.)
    isodata = np.array([[A,A,A,A,A],
                        [A,A,A,A,A],
                        [A,A,A,J,J],
                        [J,J,J,J,J],
                        [J,J,J,J,J]],dtype=np.int16)
    #make a mix of urban and rural cells
    urbdata = np.array([[R,R,R,R,R],
                        [R,U,U,U,R],
                        [R,U,U,U,U],
                        [U,U,U,R,R],
                        [R,R,R,R,R]],dtype=np.int16)
    mmidata = np.array([[6,7,8,9,6],
                        [7,8,9,6,7],
                        [8,9,6,6,7],
                        [8,9,6,7,8],
                        [9,6,7,8,9]],dtype=np.float32)
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    fatfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')
    growthfile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    geodict = GeoDict({'xmin':0.5,'xmax':4.5,'ymin':0.5,'ymax':4.5,'dx':1.0,'dy':1.0,'nx':5,'ny':5})
    
    popgrid = GMTGrid(popdata,geodict)
    isogrid = GMTGrid(isodata,geodict)
    urbgrid = GMTGrid(urbdata,geodict)
    popyear = 2016
    layers = {'mmi':mmidata}
    eventdict = {'event_id':'1234',
                 'magnitude':7.5,
                 'lat':34.2,
                 'lon':118.2,
                 'depth':10.0,
                 'event_timestamp':datetime(2016,1,1,0,0,0),
                 'event_description':'test data',
                 'event_network':'us'}
    shakedict = {'event_id':'1234',
                 'shakemap_id':'1234',
                 'shakemap_version':1,
                 'code_version':'1.0',
                 'process_timestamp':datetime.utcnow(),
                 'shakemap_originator':'us',
                 'map_status':'RELEASED',
                 'shakemap_event_type':'SCENARIO'}
    uncdict = {'mmi':(1.0,1)}
    mmigrid = ShakeGrid(layers,geodict,eventdict,shakedict,uncdict)

    popfile = isofile = urbfile = shakefile = ''
    try:
        #make some temporary files
        f,popfile = tempfile.mkstemp()
        os.close(f)
        f,isofile = tempfile.mkstemp()
        os.close(f)
        f,urbfile = tempfile.mkstemp()
        os.close(f)
        f,shakefile = tempfile.mkstemp()
        os.close(f)
        
        popgrid.save(popfile)
        isogrid.save(isofile)
        urbgrid.save(urbfile)
        mmigrid.save(shakefile)
        
        semi = SemiEmpiricalFatality.loadFromFiles(invfile,colfile,fatfile,workfile,growthfile)
        losses,resfat,nonresfat = semi.getLosses(shakefile)
        assert losses == 85
        print('Semi-empirical model calculations appear to be done correctly.')
    except:
        print('There is an error attempting to do semi-empirical loss calculations.')
    finally:
        files = [popfile,isofile,urbfile,shakefile]
        for fname in files:
            if os.path.isfile(fname):
                os.remove(fname)
    
def model_test_fake():
    A = 4 #ccode for afghanistan
    J = 392 #ccode for japan
    R = 1 #rural code
    U = 2 #urban code
    #create a 5x5 population data set with 1000 people in each cell
    popdata = np.ones((5,5))*1000.0
    #create a mixed grid of afghanistan and japan (have very different inventory,collapse, and fatality rates.)
    isodata = np.array([[A,A,A,A,A],
                        [A,A,A,A,A],
                        [A,A,A,J,J],
                        [J,J,J,J,J],
                        [J,J,J,J,J]],dtype=np.int16)
    #make a mix of urban and rural cells
    urbdata = np.array([[R,R,R,R,R],
                        [R,U,U,U,R],
                        [R,U,U,U,U],
                        [U,U,U,R,R],
                        [R,R,R,R,R]],dtype=np.int16)
    mmidata = np.array([[6,7,8,9,6],
                        [7,8,9,6,7],
                        [8,9,6,6,7],
                        [8,9,6,7,8],
                        [9,6,7,8,9]],dtype=np.float32)
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    fatfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')
    growthfile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    geodict = GeoDict({'xmin':0.5,'xmax':4.5,'ymin':0.5,'ymax':4.5,'dx':1.0,'dy':1.0,'nx':5,'ny':5})
    
    popgrid = GMTGrid(popdata,geodict)
    isogrid = GMTGrid(isodata,geodict)
    urbgrid = GMTGrid(urbdata,geodict)
    popyear = 2016
    layers = {'mmi':mmidata}
    eventdict = {'event_id':'1234',
                 'magnitude':7.5,
                 'lat':34.2,
                 'lon':118.2,
                 'depth':10.0,
                 'event_timestamp':datetime(2016,1,1,0,0,0),
                 'event_description':'test data',
                 'event_network':'us'}
    shakedict = {'event_id':'1234',
                 'shakemap_id':'1234',
                 'shakemap_version':1,
                 'code_version':'1.0',
                 'process_timestamp':datetime.utcnow(),
                 'shakemap_originator':'us',
                 'map_status':'RELEASED',
                 'shakemap_event_type':'SCENARIO'}
    uncdict = {'mmi':(1.0,1)}
    mmigrid = ShakeGrid(layers,geodict,eventdict,shakedict,uncdict)

    popfile = isofile = urbfile = shakefile = ''
    try:
        #make some temporary files
        f,popfile = tempfile.mkstemp()
        os.close(f)
        f,isofile = tempfile.mkstemp()
        os.close(f)
        f,urbfile = tempfile.mkstemp()
        os.close(f)
        f,shakefile = tempfile.mkstemp()
        os.close(f)
        
        popgrid.save(popfile)
        isogrid.save(isofile)
        urbgrid.save(urbfile)
        mmigrid.save(shakefile)
        
        semi = SemiEmpiricalFatality.loadFromFiles(invfile,colfile,fatfile,workfile,growthfile,popfile,popyear,urbfile,isofile)
        losses,resfat,nonresfat = semi.getLosses(shakefile)
        assert losses == 85
        print('Semi-empirical model calculations appear to be done correctly.')
    except:
        print('There is an error attempting to do semi-empirical loss calculations.')
    finally:
        files = [popfile,isofile,urbfile,shakefile]
        for fname in files:
            if os.path.isfile(fname):
                os.remove(fname)
    
def model_test_real():
    #test with real data
    popyear = 2012
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    fatfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')
    growthfile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    popfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_gpw.flt')
    shakefile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_grid.xml')
    
    isofile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_isogrid.bil')
    urbanfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_urban.bil')
    semi = SemiEmpiricalFatality.loadFromFiles(invfile,colfile,fatfile,workfile,growthfile)


    semi.setGlobalFiles(popfile,popyear,urbanfile,isofile)

    print('Testing semi-empirical losses...')
    losses,resfat,nonresfat = semi.getLosses(shakefile)
    testlosses = 539
    assert testlosses == losses
    print('Passed.')


def model_test_single():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    fatfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')
    growthfile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    popfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_gpw.flt')
    urbfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_urban.bil')
    isofile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_isogrid.bil')
    ccode = 'ID'
    timeofday = 'day'
    density = URBAN
    pop = 100000
    mmi = 8.5
    popyear = 2016
    semi = SemiEmpiricalFatality.loadFromFiles(invfile,colfile,fatfile,workfile,growthfile)
    #semi.setGlobalFiles(,popfile,popyear,urbfile,isofile)

    #let's do the calculations "manually" by getting all of the data and doing our own multiplications
    workforce = semi.getWorkforce(ccode)
    res,nonres,outside = pop_dist(pop,workforce,timeofday,density)
    resinv,nonresinv = semi.getInventories(ccode,density)
    res_collapse = semi.getCollapse(ccode,mmi,resinv)
    nonres_collapse = semi.getCollapse(ccode,mmi,nonresinv)
    res_fat_rates = semi.getFatalityRates(ccode,timeofday,resinv)
    nonres_fat_rates = semi.getFatalityRates(ccode,timeofday,nonresinv)
    res_fats = res * resinv * res_collapse * res_fat_rates
    nonres_fats = nonres * nonresinv * nonres_collapse * nonres_fat_rates
    #print(res_fats)
    #print(nonres_fats)
    fatsum = int(res_fats.sum()+nonres_fats.sum())
    print('Testing that "manual" calculations achieve tested result...')
    assert fatsum == 383
    print('Passed.')
    
    loss,resfat,nresfat = make_test_semi_model(invfile,colfile,fatfile,workfile,growthfile,ccode,timeofday,density,pop,mmi)
    print('Testing that "manual" calculations achieve same results as grid calculations...')
    assert fatsum == loss
    print('Passed.')
    
if __name__ == '__main__':
    #time_tests()
    #work_tests()
    model_test_single()
    model_test_real()
    

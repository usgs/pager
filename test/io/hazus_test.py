#!/usr/bin/env python

# stdlib imports
import os.path
import sys
import tempfile
import shutil
from datetime import datetime
import numpy as np
import pandas as pd

from mapio.shake import ShakeGrid

# hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
pagerdir = os.path.abspath(os.path.join(homedir, '..', '..'))
sys.path.insert(0, pagerdir)  # put this at the front of the system path, ignoring any installed shakemap stuff

# local imports
from losspager.io.hazus import HazusInfo, get_loss_string, _get_comment_str

def test_map():
    fname = os.path.join(os.path.expanduser('~'),'test_map.pdf')
    homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
    shakefile = os.path.join(homedir, '..', 'data', 'm5.8.nyc.grid.xml')
    shakegrid = ShakeGrid.load(shakefile)

    countyfile = os.path.join(homedir, '..', 'data', 'NYC_M52_sce_peak_County.shp')
    tractfile = os.path.join(homedir, '..', 'data', 'NYC_M52_sce_peak_Tract.shp')
    csvfile = os.path.join(homedir, '..', 'data', 'DamagebyCountyOccupancy.csv')
    typefile = os.path.join(homedir, '..', 'data', 'DamagebyCountyBuildingType.csv')
    hazinfo = HazusInfo(tractfile,countyfile,csvfile,typefile)
    
    hazinfo.drawHazusMap(shakegrid,fname)

def test_comment():
    few_injuries = pd.DataFrame({'CountyName':'Napa',
                                 'State':'CA',
                                 'Population':136000,
                                 'NonFatal5p':7},index=[0])
    
    several_injuries = pd.DataFrame({'CountyName':'Napa',
                                    'State':'CA',
                                    'Population':136000,
                                    'NonFatal5p':17},index=[0])
    
    dozens_injuries = pd.DataFrame({'CountyName':'Napa',
                                    'State':'CA',
                                    'Population':136000,
                                    'NonFatal5p':77},index=[0])
    
    hundreds_injuries = pd.DataFrame({'CountyName':'Napa',
                                    'State':'CA',
                                    'Population':136000,
                                    'NonFatal5p':777},index=[0])
    
    thousands_injuries = pd.DataFrame({'CountyName':'Napa',
                                    'State':'CA',
                                    'Population':136000,
                                    'NonFatal5p':7777},index=[0])

    total_pop = 100000 #use this for all shelter tests
    minimal_shelter = pd.DataFrame({'CountyName' : 'Napa',
                                   'State' : 'CA',
                                   'Households' : 49000,
                                   'DisplHouse' : 267,
                                   'Shelter' : 75},index=[0])

    considerable_shelter = pd.DataFrame({'CountyName' : 'Napa',
                                   'State' : 'CA',
                                   'Households' : 49000,
                                   'DisplHouse' : 267,
                                   'Shelter' : 750},index=[0])
    
    extensive_shelter = pd.DataFrame({'CountyName' : 'Napa',
                                   'State' : 'CA',
                                   'Households' : 49000,
                                   'DisplHouse' : 267,
                                   'Shelter' : 7500},index=[0])

    loss_thousands = pd.DataFrame({'CountyName':'Napa',
                                   'State':'CA',
                                   'Population':136000,
                                   'EconLoss':1234},index=[0])
    
    loss_tens_thousands = pd.DataFrame({'CountyName':'Napa',
                                       'State':'CA',
                                       'Population':136000,
                                       'EconLoss':12345},index=[0])

    loss_hundreds_thousands = pd.DataFrame({'CountyName':'Napa',
                                            'State':'CA',
                                            'Population':136000,
                                            'EconLoss':123456},index=[0])
    
    loss_millions = pd.DataFrame({'CountyName':'Napa',
                                  'State':'CA',
                                  'Population':136000,
                                  'EconLoss':1234567},index=[0])

    print('Shelter Tests')
    print('--------------------------------------------')
    for shelter_table in [minimal_shelter,
                          considerable_shelter,
                          extensive_shelter]:
        comment_str = _get_comment_str(loss_thousands,few_injuries, shelter_table,
                                       total_pop, 7)
        print(comment_str)
    print('--------------------------------------------')
    print()

    print('Loss Tests')
    print('--------------------------------------------')
    for loss_table in [loss_thousands,
                       loss_tens_thousands,
                       loss_hundreds_thousands,
                       loss_millions]:
        comment_str = _get_comment_str(loss_table,few_injuries, shelter_table,
                                       total_pop, 7)
        print(comment_str)
    print('--------------------------------------------')
    print()

    print('Injury Tests')
    print('--------------------------------------------')
    for injury_table in [few_injuries,
                         several_injuries,
                         dozens_injuries,
                         hundreds_injuries,
                         thousands_injuries]:
        comment_str = _get_comment_str(loss_table,injury_table, shelter_table,
                                       total_pop, 7)
        print(comment_str)
    print('--------------------------------------------')
    print()
    

def test_loss_string():
    loss, units = get_loss_string(1) # ones
    assert loss == '1' and units == ''

    loss, units = get_loss_string(7) # ones
    assert loss == '7' and units == ''
    
    loss, units = get_loss_string(12) # tens
    assert loss == '12' and units == ''
    
    loss, units = get_loss_string(123) # hundreds
    assert loss == '123' and units == ''
    
    loss, units = get_loss_string(1234) # thousands
    assert loss == '1.2' and units == 'K'
    
    loss, units = get_loss_string(12345) # tens of thousands
    assert loss == '12' and units == 'K'
    
    loss, units = get_loss_string(123456) # hundreds of thousands
    assert loss == '123' and units == 'K'
    
    loss, units = get_loss_string(1234567) # millions
    assert loss == '1.2' and units == 'M'

    loss, units = get_loss_string(1234567890) # billions
    assert loss == '1.2' and units == 'B'

    loss, units = get_loss_string(1234567890123) # trillions
    assert loss == '1.2' and units == 'T'

def test_hazus():
    homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
    countyfile = os.path.join(homedir, '..', 'data', 'NYC_M52_sce_peak_County.shp')
    tractfile = os.path.join(homedir, '..', 'data', 'NYC_M52_sce_peak_Tract.shp')
    occfile = os.path.join(homedir, '..', 'data', 'DamagebyCountyOccupancy.csv')
    typefile = os.path.join(homedir, '..', 'data', 'DamagebyCountyBuildingType.csv')
    hazinfo = HazusInfo(tractfile,countyfile,occfile,typefile)
    
    losstable,losstotals = hazinfo.getLosses()
    assert np.round(losstotals) == 4643
    
    injtable,injtotals = hazinfo.getInjuries()
    assert np.round(injtotals['Injuries']) == 448
    
    sheltable,sheltotals = hazinfo.getShelterNeeds()
    assert np.round(sheltotals['Shelter']) == 1942
    assert np.round(sheltotals['Households']) == 6793976
    assert np.round(sheltotals['DisplHouse']) == 2655
    
    debtable,debtotals = hazinfo.getDebris()
    assert np.round(debtotals['megatons']) == 598
    assert np.round(debtotals['truckloads']) == 23908

    loss_table = hazinfo.getLossTable()
    print('Losses')
    print('"%s"' % loss_table)
    print()
    
    hurt_table = hazinfo.getInjuryTable()
    print('Injuries')
    print('"%s"' % hurt_table)
    print()
    
    shel_table = hazinfo.getShelterTable()
    print('Shelter')
    print('"%s"' % shel_table)
    print()
    
    deb_table = hazinfo.getDebrisTable()
    print('Debris')
    print('"%s"' % deb_table)
    print()

    fname = os.path.join(os.path.expanduser('~'),'test_occ.pdf')
    hazinfo.plotTagging(fname)

    fname = os.path.join(os.path.expanduser('~'),'test_type.pdf')
    hazinfo.plotTypeTagging(fname)
    
    
if __name__ == '__main__':
    test_map()
    test_comment()
    test_loss_string()
    test_hazus()

#!/usr/bin/env python

#stdlib imports
import os.path
import sys

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np

#local imports
from losspager.io.xml import PagerData
from losspager.models.emploss import EmpiricalLoss
from losspager.models.exposure import Exposure
from losspager.models.econexposure import EconExposure
from losspager.models.growth import PopulationGrowth
from losspager.models.semimodel import SemiEmpiricalFatality
from mapio.city import Cities

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    fatfile = os.path.join(homedir,'..','data','fatality.xml')
    ecofile = os.path.join(homedir,'..','data','economy.xml')
    cityfile = os.path.join(homedir,'..','data','cities1000.txt')
    ratefile = os.path.join(homedir,'..','data','WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    gdpfile = os.path.join(homedir,'..','data','API_NY.GDP.PCAP.CD_DS2_en_excel_v2.xls')
    event = 'northridge'
    shakefile = os.path.join(homedir,'..','data','eventdata',event,'%s_grid.xml' % event)
    popfile = os.path.join(homedir,'..','data','eventdata',event,'%s_gpw.flt' % event)
    isofile = os.path.join(homedir,'..','data','eventdata',event,'%s_isogrid.bil' % event)
    urbanfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_urban.bil')
    
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    casfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')

    popyear = 2012

    semi = SemiEmpiricalFatality.fromDefault()
    semi.setGlobalFiles(popfile,popyear,urbanfile,isofile)
    semiloss,resfat,nonresfat = semi.getLosses(shakefile)
    
    popgrowth = PopulationGrowth.fromDefault()
    econexp = EconExposure(popfile,2012,isofile)
    fatmodel = EmpiricalLoss.fromDefaultFatality()
    expobject = Exposure(popfile,2012,isofile,popgrowth)

    
    expdict = expobject.calcExposure(shakefile)
    fatdict = fatmodel.getLosses(expdict)
    econexpdict = econexp.calcExposure(shakefile)
    ecomodel = EmpiricalLoss.fromDefaultEconomic()
    ecodict = ecomodel.getLosses(expdict)
    shakegrid = econexp.getShakeGrid()
    pagerversion = 1
    cities = Cities.loadFromGeoNames(cityfile)
    impact1 = '''Red alert level for economic losses. Extensive damage is probable 
    and the disaster is likely widespread. Estimated economic losses are less 
    than 1% of GDP of Italy. Past events with this alert level have required 
    a national or international level response.'''
    impact2 = '''Orange alert level for shaking-related fatalities. Significant 
    casualties are likely.'''
    structcomment = '''Overall, the population in this region resides in structures 
    that are a mix of vulnerable and earthquake resistant construction. The predominant 
    vulnerable building types are unreinforced brick with mud and mid-rise nonductile 
    concrete frame with infill construction.'''
    histeq = [1,2,3]
    secondarycomment = '''Recent earthquakes in this area have caused secondary hazards 
    such as landslides that might have contributed to losses.'''
    doc = PagerData()
    
    

if __name__ == '__main__':
    test()

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
from losspager.models.semimodel import SemiEmpiricalFatality
from losspager.onepager.comment import get_impact_comments,get_structure_comment

def test_impact():
    #both impacts are green
    tz_exp = np.array([0,0,0,102302926316,13976446978,9127080479,7567231,0,0,0])
    ug_exp = np.array([0,0,240215309,255785480321,33062696103,1965288263,0,0,0,0])
    econexp = {'TZ':tz_exp,
               'UG':ug_exp,
               'TotalEconomicExposure':tz_exp+ug_exp}
    fatdict = {'TZ':0,
               'UG':0,
               'TotalFatalities':0}
    ecodict = {'TZ':283,
               'UG':262049,
               'TotalDollars':262332}
    event_year = 2016
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c1 = 'Green alert for shaking-related fatalities and economic losses. There is a low likelihood of casualties and damage.'
    assert impact1 == impact1_c1
    assert impact2 == ''

    #fatalities are yellow
    fatdict = {'TZ':0,
               'UG':1,
               'TotalFatalities':1}
    ecodict = {'TZ':283,
               'UG':262049,
               'TotalDollars':262332}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c2 = 'Some casualties are possible and the impact should be relatively localized. Past events with this alert level have required a local or regional level response.'
    impact2_c2 = 'There is a low likelihood of damage.'
    assert impact1 == impact1_c2
    assert impact2 == impact2_c2

    #fatalities are orange
    fatdict = {'TZ':0,
               'UG':101,
               'TotalFatalities':101}
    ecodict = {'TZ':283,
               'UG':262049,
               'TotalDollars':262332}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c3 = 'Significant casualties are likely and the disaster is potentially widespread. Past events with this alert level have required a regional or national level response.'
    impact2_c3 = 'There is a low likelihood of damage.'
    assert impact1 == impact1_c3
    assert impact2 == impact2_c3

    #fatalities are red
    fatdict = {'TZ':0,
               'UG':1001,
               'TotalFatalities':1001}
    ecodict = {'TZ':283,
               'UG':262049,
               'TotalDollars':262332}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c4 = 'High casualties are probable and the disaster is likely widespread. Past events with this alert level have required a national or international level response.'
    impact2_c4 = 'There is a low likelihood of damage.'
    assert impact1 == impact1_c4
    assert impact2 == impact2_c4

    #econ losses are yellow
    fatdict = {'TZ':0,
               'UG':0,
               'TotalFatalities':0}
    ecodict = {'TZ':0,
               'UG':1000001,
               'TotalDollars':1000001}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Some damage is possible and the impact should be relatively localized. Estimated economic losses are less than 1% of GDP of Uganda. Past events with this alert level have required a local or regional level response.'
    impact2_c5 = 'There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #econ losses are orange
    fatdict = {'TZ':0,
               'UG':0,
               'TotalFatalities':0}
    ecodict = {'TZ':0,
               'UG':100e6+1,
               'TotalDollars':100e6+1}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Significant damage is likely and the disaster is potentially widespread. Estimated economic losses are 0-1% GDP of Uganda. Past events with this alert level have required a regional or national level response.'
    impact2_c5 = 'There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #econ losses are red
    fatdict = {'TZ':0,
               'UG':0,
               'TotalFatalities':0}
    ecodict = {'TZ':0,
               'UG':1000e6+1,
               'TotalDollars':1000e6+1}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Extensive damage is probable and the disaster is likely widespread. Estimated economic losses are 1-10% GDP of Uganda.  Past events with this alert level have required a national or international level response.'
    impact2_c5 = 'There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #econ losses are REALLY red
    fatdict = {'TZ':0,
               'UG':0,
               'TotalFatalities':0}
    ecodict = {'TZ':0,
               'UG':15e9,
               'TotalDollars':15e9}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Extensive damage is probable and the disaster is likely widespread. Estimated economic losses may exceed the GDP of Uganda.  Past events with this alert level have required a national or international level response.'
    impact2_c5 = 'There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #both alerts are yellow
    fatdict = {'TZ':0,
               'UG':1,
               'TotalFatalities':1}
    ecodict = {'TZ':0,
               'UG':1e6+1,
               'TotalDollars':1e6+1}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Yellow alert for shaking-related fatalities and economic losses. Some casualties and damage are possible and the impact should be relatively localized. Past yellow alerts have required a local or regional level response.'
    impact2_c5 = 'Estimated economic losses are less than 1% of GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #both alerts are orange
    fatdict = {'TZ':0,
               'UG':101,
               'TotalFatalities':101}
    ecodict = {'TZ':0,
               'UG':100e6+1,
               'TotalDollars':100e6+1}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Orange alert for shaking-related fatalities and economic losses. Significant casualties and damage are likely and the disaster is potentially widespread. Past orange alerts have required a regional or national level response.'
    impact2_c5 = 'Estimated economic losses are 0-1% GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    #both alerts are red
    fatdict = {'TZ':0,
               'UG':1001,
               'TotalFatalities':1001}
    ecodict = {'TZ':0,
               'UG':1e9+1,
               'TotalDollars':1e9+1}
    impact1,impact2 = get_impact_comments(fatdict,ecodict,econexp,event_year)
    impact1_c5 = 'Red alert for shaking-related fatalities and economic losses. High casualties and extensive damage are probable and the disaster is likely widespread. Past red alerts have required a national or international response.'
    impact2_c5 = 'Estimated economic losses are 1-10% GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

def test_structure():
    resfat = {'IN':{'A1':434,'A2':837},
              'NP':{'UFB':200,'W1':100}}
    nonresfat = {'IN':{'A1':434,'A2':837},
                 'NP':{'UFB':200,'W1':100}}
    semimodel = SemiEmpiricalFatality.fromDefault()
    structure_comment = get_structure_comment(resfat,nonresfat,semimodel)
    cmpstr = 'Overall, the population in this region resides in structures that are vulnerable to earthquake shaking, though resistant structures exist.  The predominant vulnerable building type is adobe block with light roof construction.'
    assert structure_comment == cmpstr

if __name__ == '__main__':
    test_structure()
    test_impact()
    

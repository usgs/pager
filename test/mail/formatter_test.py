#!/usr/bin/env python

#stdlib imports
import tempfile
import os.path
import sys
import json
from datetime import datetime
import shutil
from textwrap import dedent
import re

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

#local imports
from losspager.mail.formatter import format_exposure,format_city_table,\
     format_earthquakes,format_msg,format_short,format_long
from losspager.schema import emailschema as es

def test_format_exposure():
    exposures = [0,
                 0,
                 5999397,
                 7734572,
                 8041148,
                 2670694,
                 869317,
                 947968,
                 54893,
                 654]
    shortstr = format_exposure(exposures,'short',5)
    str1 = '''
    I9=56,000
    I8=948,000
    I7=869,000
    I6=2,671,000
    I5=8,041,000
    I4=7,735,000
    I3=5,999,000
    '''
    str1 = dedent(str1).lstrip()
    assert shortstr == str1
    print(shortstr)
    longstr = format_exposure(exposures,'long',5)
    print(longstr)
    str2 = '''Estimated\tPopulation\tExposure
    MMI9\t56,000
    MMI8\t948,000
    MMI7\t869,000
    MMI6\t2,671,000
    MMI5\t8,041,000
    MMI4\t7,735,000*
    MMI3\t5,999,000*
    *\t-\tMMI\tlevel\textends\tbeyond\tmap\tboundary,\tactual\tpopulation\texposure\tmay\tbe\tlarger.
    '''
    str2 = dedent(str2).strip()
    newlongstr = ''
    for line in longstr.split('\n'):
        parts = line.split()
        newline = '\t'.join(parts)+'\n'
        newlongstr += newline

    str2_stripped = re.sub('\s+','',str2)
    newlongstr_stripped = re.sub('\s+','',newlongstr)
    assert newlongstr_stripped == str2_stripped

def test_format_city_table():
    cities = [{'pop':27978, 'name':"Aso", 'mmi':8.41},
              {'pop':39234, 'name':"Uto", 'mmi':8.29},
              {'pop':29820, 'name':"Ozu", 'mmi':8.27},
              {'pop':26163, 'name':"Matsubase", 'mmi':7.92},
              {'pop':680423, 'name':"Kumamoto", 'mmi':7.77},
              {'pop':31688, 'name':"Ueki", 'mmi':7.11},
              {'pop':1392289, 'name':"Fukuoka", 'mmi':5.43},
              {'pop':555352, 'name':"Kagoshima", 'mmi':5.39},
              {'pop':1143841, 'name':"Hiroshima", 'mmi':4.23},
              {'pop':550000, 'name':"Changwon", 'mmi':3.43},
              {'pop':3678555, 'name':"Busan", 'mmi':3.35}]

    dataframe = pd.DataFrame(cities)
    city_table = format_city_table(dataframe)
    print(city_table)
    str1 = '''
    MMI   City                           Population
    VIII  Aso                            28,000
    VIII  Uto                            39,000
    VIII  Ozu                            30,000
    VII   Matsubase                      26,000
    VII   Kumamoto                       680,000
    VII   Ueki                           32,000
    V     Fukuoka                        1,392,000
    V     Kagoshima                      555,000
    IV    Hiroshima                      1,144,000
    III   Changwon                       550,000
    III   Busan                          3,679,000'''
    str1 = dedent(str1).strip()
    city_table = city_table.strip()
    newstr1 = ''
    for line in str1.split('\n'):
        parts = line.split()
        newline = '\t'.join(parts)+'\n'
        newstr1 += newline
    newtable = ''
    for line in city_table.split('\n'):
        parts = line.split()
        newline = '\t'.join(parts)+'\n'
        newtable += newline
    assert newstr1 == newtable

# def test_format_msg():
#     etime = datetime(2016,3,1,12,34,56)
#     version = es.Version(versioncode='us20005iis',
#                          time=etime,
#                          lat = 32.7931,
#                          lon = 130.7486,
#                          depth = 10.0,
#                          magnitude=7.0,
#                          number=1,
#                          maxmmi = 9.0,
#                          summarylevel='red')

#     exposures = [{'inside':False, 'exposure':0},
#                  {'inside':False, 'exposure':0},
#                  {'inside':False, 'exposure':5999397},
#                  {'inside':False, 'exposure':7734572},
#                  {'inside':False, 'exposure':8041148},
#                  {'inside':False, 'exposure':2670694},
#                  {'inside':False, 'exposure':869317},
#                  {'inside':False, 'exposure':947968},
#                  {'inside':False, 'exposure':54893},
#                  {'inside':False, 'exposure':654}]
    
#     expstr = format_exposure(exposures,'short')
#     shortmsg = format_short(version,expstr)

#     cmpstr = '''
#     M7.0
#     D10
#     2016/03/01-12:34
#     (32.793,130.749)
#     ALERT:Red
#     I9=56,000
#     I8=948,000
#     I7=869,000
#     I6=2,671,000
#     I5=8,041,000
#     I4=7,735,000
#     I3=5,999,000
#     '''
#     cmpstr = dedent(cmpstr)
#     assert shortmsg == cmpstr

#     print(shortmsg)
#     cities = [{'pop':27978, 'name':"Aso", 'mmi':8.41},
#               {'pop':39234, 'name':"Uto", 'mmi':8.29},
#               {'pop':29820, 'name':"Ozu", 'mmi':8.27},
#               {'pop':26163, 'name':"Matsubase", 'mmi':7.92},
#               {'pop':680423, 'name':"Kumamoto", 'mmi':7.77},
#               {'pop':31688, 'name':"Ueki", 'mmi':7.11},
#               {'pop':1392289, 'name':"Fukuoka", 'mmi':5.43},
#               {'pop':555352, 'name':"Kagoshima", 'mmi':5.39},
#               {'pop':1143841, 'name':"Hiroshima", 'mmi':4.23},
#               {'pop':550000, 'name':"Changwon", 'mmi':3.43},
#               {'pop':3678555, 'name':"Busan", 'mmi':3.35}]

#     historical_events = [{'distance':363.70022777,'magnitude':6.7, 
#                           'maxmmi':9, 'deaths':0, 'date':datetime(2000,10,6,4,30,20),'maxmmiexp':37718},
#                          {'distance':120.744540337, 'magnitude':6.6, 
#                           'maxmmi':9, 'deaths':1, 'date':datetime(2005,3,20,1,53,42), 'maxmmiexp':73948},
#                          {'distance':220.632206626, 'magnitude':6.8, 
#                           'maxmmi':8, 'deaths':2, 'date':datetime(2001,3,24,6,27,53), 'maxmmiexp':4737}]

#     eventinfo = {}
#     eventinfo['location'] = 'KYUSHU, JAPAN'
#     eventinfo['fatalert'] = 'orange'
#     eventinfo['ecoalert'] = 'red'
#     eventinfo['tsunami'] = 1
#     eventinfo['exposure'] = exposures
#     eventinfo['cities'] = cities
#     eventinfo['impact_comment'] = '''Red alert level for economic losses.  Extensive damage is probable
#     and the disaster is likely widespread. Estimated economic losses
#     are less than 1% of GDP of Japan. Past events with this alert
#     level have required a national or international level
#     response. Orange alert level for shaking-related fatalities.
#     Significant casualties are likely.'''
#     eventinfo['structure_comment'] = '''Overall, the population in this region resides in structures that
#     are resistant to earthquake shaking, though some vulnerable
#     structures exist.  The predominant vulnerable building types are
#     low-rise concrete wall and heavy wood frame construction.'''
#     eventinfo['secondary_comment'] = '''Recent earthquakes in this area have caused secondary hazards such
#     as tsunamis and landslides that might have contributed to losses.'''
#     eventinfo['historical_earthquakes'] = historical_events
#     eventinfo['url'] = 'http://earthquake.usgs.gov/earthquakes/eventpage/us20005iis'
#     expstr = format_exposure(exposures,'long')
#     longmsg = format_long(version,eventinfo,expstr)
#     print('Long message:')
#     print(longmsg)
    

if __name__ == '__main__':
    test_format_exposure()
    test_format_city_table()
    #test_format_msg()
    
    

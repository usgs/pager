#!/usr/bin/env python

#stdlib imports
import os.path
import sys
import tempfile
import shutil

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np

#local imports
from losspager.io.pagerdata import PagerData
from losspager.models.emploss import EmpiricalLoss
from losspager.models.exposure import Exposure
from losspager.models.econexposure import EconExposure
from losspager.models.growth import PopulationGrowth
from losspager.models.semimodel import SemiEmpiricalFatality
from losspager.vis.contourmap2 import draw_contour
from mapio.city import Cities

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    fatfile = os.path.join(homedir,'..','data','fatality.xml')
    ecofile = os.path.join(homedir,'..','data','economy.xml')
    cityfile = os.path.join(homedir,'..','data','cities1000.txt')
    event = 'northridge'
    shakefile = os.path.join(homedir,'..','data','eventdata',event,'%s_grid.xml' % event)
    popfile = os.path.join(homedir,'..','data','eventdata',event,'%s_gpw.flt' % event)
    isofile = os.path.join(homedir,'..','data','eventdata',event,'%s_isogrid.bil' % event)
    urbanfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_urban.bil')
    oceanfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_ocean.json')
    
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    casfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')

    tdir = tempfile.mkdtemp()
    outfile = os.path.join(tdir,'output.pdf')
    pngfile,mapcities = draw_contour(shakefile,popfile,oceanfile,cityfile,outfile,make_png=True)
    shutil.rmtree(tdir)
    
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
    struct_comment = '''Overall, the population in this region resides
    in structures that are resistant to earthquake
    shaking, though some vulnerable structures
    exist.'''
    secondary_comment = '''Recent earthquakes in this area have caused secondary hazards 
    such as landslides that might have contributed to losses.'''
    hist_comment = ''''A magnitude 7.1 earthquake 240 km east of this event struck Reventador: Ecuador 
    on March 6, 1987 (UTC), with estimated population exposures of 14,000 at intensity VIII and 2,000 
    at intensity IX or greater, resulting in a reported 5,000 fatalities.'''.replace('\n','')
    doc = PagerData()
    doc.setInputs(shakegrid,pagerversion,shakegrid.getEventDict()['event_id'])
    doc.setExposure(expdict,econexpdict)
    doc.setModelResults(fatmodel,ecomodel,
                        fatdict,ecodict,
                        semiloss,resfat,nonresfat)
    doc.setComments(impact1,impact2,struct_comment,hist_comment,secondary_comment)
    doc.setMapInfo(cityfile,mapcities)
    doc.validate()

    eventinfo = doc.getEventInfo()
    assert eventinfo['mag'] == shakegrid.getEventDict()['magnitude']
    
    imp1,imp2 = doc.getImpactComments()
    assert imp1 == impact1 and imp2 == impact2

    version = doc.getSoftwareVersion()
    elapsed = doc.getElapsed()

    exp = doc.getTotalExposure()
    assert np.isclose(np.array(exp),expdict['TotalExposure']).all()

    hist_table = doc.getHistoricalTable()
    assert hist_table[0]['EventID'] == '199206281505'

    scomm = doc.getStructureComment()
    assert scomm == struct_comment
    
    hcomm = doc.getHistoricalComment()
    assert hcomm == hist_comment

    citytable = doc.getCityTable()
    assert citytable.iloc[0]['name'] == 'Santa Clarita'

    summary = doc.getSummaryAlert()
    assert summary == yellow
    
    
if __name__ == '__main__':
    test()

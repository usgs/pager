#!/usr/bin/env python

#stdlib imports
import os.path
import sys
import tempfile
import shutil
from datetime import datetime

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
from mapio.shake import getHeaderData

#local imports
from losspager.io.pagerdata import PagerData
from losspager.models.emploss import EmpiricalLoss
from losspager.models.exposure import Exposure
from losspager.models.econexposure import EconExposure
from losspager.models.growth import PopulationGrowth
from losspager.models.semimodel import SemiEmpiricalFatality
from losspager.vis.contourmap2 import draw_contour
from mapio.city import Cities

DATETIMEFMT = '%Y-%m-%d %H:%M:%S'
TSUNAMI_MAG_THRESH = 7.3

def tdoc(doc,shakegrid,impact1,impact2,expdict,struct_comment,hist_comment,):
    eventinfo = doc.getEventInfo()
    assert eventinfo['mag'] == shakegrid.getEventDict()['magnitude']
    
    imp1,imp2 = doc.getImpactComments()
    assert imp1 == impact1 and imp2 == impact2

    version = doc.getSoftwareVersion()
    elapsed = doc.getElapsed()

    exp = doc.getTotalExposure()
    assert np.isclose(np.array(exp),expdict['TotalExposure']).all()

    hist_table = doc.getHistoricalTable()
    assert hist_table[0]['EventID'] == '198411261621'

    scomm = doc.getStructureComment()
    assert scomm == struct_comment
    
    hcomm = doc.getHistoricalComment()
    assert hcomm == hist_comment

    citytable = doc.getCityTable()
    assert citytable.iloc[0]['name'] == 'Santa Clarita'

    summary = doc.getSummaryAlert()
    assert summary == 'yellow'

    #test property methods
    assert doc.magnitude == shakegrid.getEventDict()['magnitude']
    assert doc.time == shakegrid.getEventDict()['event_timestamp']
    assert doc.summary_alert == 'yellow'
    assert doc.processing_time == datetime.strptime(doc._pagerdict['pager']['processing_time'],DATETIMEFMT)
    assert doc.version == doc._pagerdict['pager']['version_number']

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
    oceangridfile = os.path.join(homedir,'..','data','eventdata','northridge','northridge_ocean.bil')
    
    invfile = os.path.join(homedir,'..','data','semi_inventory.hdf')
    colfile = os.path.join(homedir,'..','data','semi_collapse_mmi.hdf')
    casfile = os.path.join(homedir,'..','data','semi_casualty.hdf')
    workfile = os.path.join(homedir,'..','data','semi_workforce.hdf')

    tdir = tempfile.mkdtemp()
    basename = os.path.join(tdir,'output')
    pdffile,pngfile,mapcities = draw_contour(shakefile,popfile,oceanfile,oceangridfile,cityfile,basename)
    shutil.rmtree(tdir)
    
    popyear = 2012

    shake_tuple = getHeaderData(shakefile)
    tsunami = shake_tuple[1]['magnitude'] >= TSUNAMI_MAG_THRESH
    
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

    location = 'At the top of the world.'
    
    doc = PagerData()
    eventcode = shakegrid.getEventDict()['event_id']
    versioncode = eventcode
    doc.setInputs(shakegrid,pagerversion,versioncode,eventcode,tsunami,location)
    doc.setExposure(expdict,econexpdict)
    doc.setModelResults(fatmodel,ecomodel,
                        fatdict,ecodict,
                        semiloss,resfat,nonresfat)
    doc.setComments(impact1,impact2,struct_comment,hist_comment,secondary_comment)
    doc.setMapInfo(cityfile,mapcities)
    doc.validate()

    #let's test the property methods
    
    
    tdoc(doc,shakegrid,impact1,impact2,expdict,struct_comment,hist_comment)
    

    #see if we can save this to a bunch of files then read them back in
    try:
        tdir = tempfile.mkdtemp()
        doc.saveToJSON(tdir)
        newdoc = PagerData()
        newdoc.loadFromJSON(tdir)
        tdoc(newdoc,shakegrid,impact1,impact2,expdict,struct_comment,hist_comment)

        #test the xml saving method
        xmlfile = doc.saveToLegacyXML(tdir)
    except Exception as e:
        assert 1==2
    finally:
        shutil.rmtree(tdir)

    
    
if __name__ == '__main__':
    test()

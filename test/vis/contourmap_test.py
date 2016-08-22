#!/usr/bin/env python

#stdlib imports
import tempfile
import os.path
import sys
from collections import OrderedDict
import warnings
import shutil

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
import matplotlib.pyplot as plt
from mapio.shake import ShakeGrid
from mapio.gdal import GDALGrid
from mapio.basemapcity import BasemapCities

#local imports
from losspager.vis.contourmap import PAGERMap

def test():
    homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
    datadir = os.path.abspath(os.path.join(homedir,'..','data','eventdata','northridge'))
    cityfile = os.path.join(datadir,'northridge_cities.txt')
    coastfile = os.path.join(datadir,'northridge_coastline.json')
    countryfile = os.path.join(datadir,'northridge_countries.json')
    statefile = os.path.join(datadir,'northridge_states.json')
    lakefile = os.path.join(datadir,'northridge_lakes.json')
    oceanfile = os.path.join(datadir,'northridge_ocean.json')
    shakefile = os.path.join(datadir,'northridge_grid.xml')
    popfile = os.path.join(datadir,'northridge_gpw.flt')
    layerdict = {'coast':coastfile,
                 'ocean':oceanfile,
                 'lake':lakefile,
                 'country':countryfile,
                 'state':statefile}
    #get shakemap geodict
    shakedict = ShakeGrid.getFileGeoDict(shakefile,adjust='res')
    #get population geodict
    popdict = GDALGrid.getFileGeoDict(popfile)
    sampledict = popdict.getBoundsWithin(shakedict)
    
    shakegrid = ShakeGrid.load(shakefile,samplegeodict=sampledict,resample=True,method='linear',adjust='res')
    popgrid = GDALGrid.load(popfile,samplegeodict=sampledict,resample=False)
    cities = BasemapCities.loadFromCSV(cityfile)
    print('Testing to see if PAGER can successfully create contour map...')
    try:
        outfolder = tempfile.mkdtemp()
        pmap = PAGERMap(shakegrid,popgrid,cities,layerdict,outfolder)
        pmap.drawContourMap()
    except Exception as error:
        raise error
    finally:
        if os.path.isdir(outfolder):
            shutil.rmtree(outfolder)
    print('Passed.')
     
if __name__ == '__main__':
    warnings.filterwarnings("ignore")
    test()

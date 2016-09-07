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

#local imports
from losspager.vis.contourmap2 import draw_contour

def test(outfolder=None):
    topdata = os.path.abspath(os.path.join(homedir,'..','data'))
    datadir = os.path.abspath(os.path.join(topdata,'eventdata','northridge'))
    
    cityfile = os.path.join(topdata,'cities1000.txt')
    oceanfile = os.path.join(datadir,'northridge_ocean.json')
    shakefile = os.path.join(datadir,'northridge_grid.xml')
    popfile = os.path.join(datadir,'northridge_gpw.flt')
    print('Testing to see if PAGER can successfully create contour map...')
    hasfolder = False
    if outfolder is not None:
        hasfolder = True
    try:
        if not hasfolder:
            outfolder = tempfile.mkdtemp()
        outfile = os.path.join(outfolder,'output.pdf')
        pngfile = draw_contour(shakefile,popfile,oceanfile,cityfile,outfile,make_png=True)
        print('Output pdf is %s, output png is %s.' % (outfile,pngfile))

        assert os.path.isfile(pngfile) and os.path.isfile(outfile)
    except Exception as error:
        raise error
    finally:
        if os.path.isdir(outfolder) and not hasfolder:
            shutil.rmtree(outfolder)
    print('Passed.')
     
if __name__ == '__main__':
    warnings.filterwarnings("ignore")
    test(outfolder=os.path.expanduser('~'))

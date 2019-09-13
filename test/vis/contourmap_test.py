#!/usr/bin/env python

# stdlib imports
import tempfile
import os.path
import warnings
import shutil

# local imports
from losspager.vis.contourmap import draw_contour
from losspager.models.exposure import Exposure


def test(outfolder=None):
    homedir = os.path.dirname(os.path.abspath(__file__))
    topdata = os.path.abspath(os.path.join(homedir, '..', 'data'))
    datadir = os.path.abspath(os.path.join(topdata, 'eventdata', 'northridge'))

    cityfile = os.path.join(topdata, 'cities1000.txt')
    oceanfile = os.path.join(datadir, 'northridge_ocean.json')
    shakefile = os.path.join(datadir, 'northridge_grid.xml')
    popfile = os.path.join(datadir, 'northridge_gpw.flt')
    ogridfile = os.path.join(datadir, 'northridge_ocean.bil')
    isofile = os.path.join(datadir, 'northridge_isogrid.bil')

    exp = Exposure(popfile, 2012, isofile)
    results = exp.calcExposure(shakefile)
    shakegrid = exp.getShakeGrid()
    popgrid = exp.getPopulationGrid()

    print('Testing to see if PAGER can successfully create contour map...')
    hasfolder = False
    if outfolder is not None:
        hasfolder = True
    try:
        if not hasfolder:
            outfolder = tempfile.mkdtemp()
        basefile = os.path.join(outfolder, 'output')
        pdffile, pngfile, mapcities = draw_contour(
            shakegrid, popgrid, oceanfile, ogridfile, cityfile, basefile)
        print('Output pdf is %s, output png is %s.' % (pdffile, pngfile))

        assert os.path.isfile(pngfile) and os.path.isfile(pdffile)
    except Exception as error:
        raise error
    finally:
        if os.path.isdir(outfolder) and not hasfolder:
            shutil.rmtree(outfolder)
    print('Passed.')


if __name__ == '__main__':
    warnings.filterwarnings("ignore")
    outfolder = os.path.expanduser('~')
    test(outfolder=outfolder)

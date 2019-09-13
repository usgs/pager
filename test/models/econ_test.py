#!/usr/bin/env python

# stdlib imports
import os.path

# third party imports
import numpy as np
import fiona

# local imports
from losspager.models.emploss import EmpiricalLoss, LognormalModel
from losspager.models.econexposure import EconExposure


def test():
    event = 'northridge'
    homedir = os.path.dirname(os.path.abspath(
        __file__))  # where is this script?
    shakefile = os.path.join(homedir, '..', 'data',
                             'eventdata', event, '%s_grid.xml' % event)
    popfile = os.path.join(homedir, '..', 'data',
                           'eventdata', event, '%s_gpw.flt' % event)
    isofile = os.path.join(homedir, '..', 'data',
                           'eventdata', event, '%s_isogrid.bil' % event)
    shapefile = os.path.join(homedir, '..', 'data', 'eventdata',
                             event, 'City_BoundariesWGS84',
                             'City_Boundaries.shp')

    print('Test loading economic exposure from inputs...')
    econexp = EconExposure(popfile, 2012, isofile)
    print('Passed loading economic exposure from inputs...')

    print('Test loading empirical fatality model from XML file...')
    ecomodel = EmpiricalLoss.fromDefaultEconomic()
    print('Passed loading empirical fatality model from XML file.')

    print('Testing calculating probabilities for standard PAGER ranges...')
    expected = {'UK': 6819.883892 * 1e6, 'TotalDollars': 6819.883892 * 1e6}
    G = 2.5
    probs = ecomodel.getProbabilities(expected, G)
    testprobs = {'0-1': 0.00020696841425738358,
                 '1-10': 0.0043200811319132086,
                 '10-100': 0.041085446477813294,
                 '100-1000': 0.17564981840854255,
                 '1000-10000': 0.33957681768639003,
                 '10000-100000': 0.29777890303065313,
                 '100000-10000000': 0.14138196485040311}
    for key, value in probs.items():
        np.testing.assert_almost_equal(value, testprobs[key])
    msg = ('Passed combining G values from all countries that '
           'contributed to losses...')
    print(msg)

    print('Test retrieving economic model data from XML file...')
    model = ecomodel.getModel('af')
    testmodel = LognormalModel(
        'dummy', 9.013810, 0.100000, 4.113200, alpha=15.065400)
    assert model == testmodel
    print('Passed retrieving economic model data from XML file.')

    print('Testing with known exposures/losses for 1994 Northridge EQ...')
    exposure = {'xf': np.array([0, 0, 556171936.807, 718990717350.0,
                                2.40385709638e+12, 2.47073141687e+12,
                                1.2576210799e+12, 698888019337.0,
                                1913733716.16, 0.0])}
    expodict = ecomodel.getLosses(exposure)
    testdict = {'xf': 25945225582}
    assert expodict['xf'] == testdict['xf']
    msg = ('Passed testing with known exposures/fatalities for '
           '1994 Northridge EQ.')
    print(msg)

    print('Testing calculating total economic losses for Northridge...')
    expdict = econexp.calcExposure(shakefile)
    ecomodel = EmpiricalLoss.fromDefaultEconomic()
    lossdict = ecomodel.getLosses(expdict)
    testdict = {'XF': 23172277187}
    assert lossdict['XF'] == testdict['XF']
    print('Passed calculating total economic losses for Northridge...')

    print('Testing creating a economic loss grid...')
    mmidata = econexp.getShakeGrid().getLayer('mmi').getData()
    popdata = econexp.getEconPopulationGrid().getData()
    isodata = econexp.getCountryGrid().getData()
    ecogrid = ecomodel.getLossGrid(mmidata, popdata, isodata)
    ecosum = 23172275857.094917
    assert np.nansum(ecogrid) == ecosum
    print('Passed creating a economic loss grid.')

    print('Testing assigning economic losses to polygons...')
    popdict = econexp.getPopulationGrid().getGeoDict()
    shapes = []
    f = fiona.open(shapefile, 'r')
    for row in f:
        shapes.append(row)
    f.close()
    ecoshapes, toteco = ecomodel.getLossByShapes(
        mmidata, popdata, isodata, shapes, popdict)
    ecoshapes = sorted(ecoshapes,
                       key=lambda shape: shape['properties']['dollars_lost'],
                       reverse=True)
    lalosses = 17323352577
    for shape in ecoshapes:
        if shape['id'] == '312':  # Los Angeles
            cname = shape['properties']['CITY_NAME']
            dollars = shape['properties']['dollars_lost']
            assert lalosses == dollars
            assert cname == 'Los Angeles'
    print('Passed assigning economic losses to polygons...')


if __name__ == '__main__':
    test()

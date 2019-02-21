#!/usr/bin/env python

# stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys
from datetime import datetime
from collections import OrderedDict

# third party imports
import numpy as np
from mapio.geodict import GeoDict
from mapio.gmt import GMTGrid
from mapio.grid2d import Grid2D
from mapio.shake import ShakeGrid
import fiona

# local imports
from losspager.models.emploss import EmpiricalLoss, LognormalModel
from losspager.models.exposure import Exposure
from losspager.models.growth import PopulationGrowth


def get_temp_file_name():
    foo, tmpfile = tempfile.mkstemp()
    os.close(foo)
    return tmpfile


def lognormal_object_test():
    model_dict = {'AF': (11.613073, 0.180683),
                  'CN': (10.328811, 0.100058),
                  'JP': (11.862534, 0.100779),
                  'US': (46.155474, 0.434135),
                  'IR': (9.318099, 0.100001)}

    model1 = LognormalModel('IR', 9.318099, 0.100001, 0.0)
    model2 = LognormalModel('US', 46.155474, 0.434135, 0.0)
    model3 = LognormalModel('IR', 10.986839, 0.128601, 0.0)

    print('Testing that fatality rates calculation is correct...')
    rates = model3.getLossRates(np.arange(5, 10))
    testrates = np.array([4.62833172e-10, 1.27558914e-06,
                          2.28027416e-04, 6.81282956e-03, 6.04383822e-02])
    np.testing.assert_almost_equal(rates, testrates)
    print('Fatality rates calculation is correct.')

    print('Testing model fatality comparison...')
    assert model1 > model2
    print('Passed model fatality comparison.')

    print('More complete test of model fatality comparison...')
    mlist = []
    for key, values in model_dict.items():
        mlist.append(LognormalModel(key, values[0], values[1], 0.0))

    mlist.sort()
    names = [m.name for m in mlist]
    assert names != ['JP', 'US', 'CN', 'IR', 'AF']
    print('Passed more complete test of model fatality comparison.')

    print('Sorted list of country models:')
    print('%5s %6s %6s %-6s %-14s' %
          ('Name', 'Theta', 'Beta', 'Area', 'Deaths'))
    for model in mlist:
        exp_pop = np.array([1e6, 1e6, 1e6, 1e6, 1e6])
        mmirange = np.arange(5, 10)
        deaths = model.getLosses(exp_pop, mmirange)
        print('%5s %6.3f %6.3f %6.4f %14.4f' %
              (model.name, model.theta, model.beta, model.getArea(), deaths))


def basic_test():

    mmidata = np.array([[7, 8, 8, 8, 7],
                        [8, 9, 9, 9, 8],
                        [8, 9, 10, 9, 8],
                        [8, 9, 9, 8, 8],
                        [7, 8, 8, 6, 5]], dtype=np.float32)
    popdata = np.ones_like(mmidata) * 1e7
    isodata = np.array([[4, 4, 4, 4, 4],
                        [4, 4, 4, 4, 4],
                        [4, 4, 156, 156, 156],
                        [156, 156, 156, 156, 156],
                        [156, 156, 156, 156, 156]], dtype=np.int32)

    shakefile = get_temp_file_name()
    popfile = get_temp_file_name()
    isofile = get_temp_file_name()
    geodict = GeoDict({'xmin': 0.5, 'xmax': 4.5, 'ymin': 0.5,
                       'ymax': 4.5, 'dx': 1.0, 'dy': 1.0, 'nx': 5, 'ny': 5})
    layers = OrderedDict([('mmi', mmidata), ])
    event_dict = {'event_id': 'us12345678', 'magnitude': 7.8,
                  'depth': 10.0, 'lat': 34.123, 'lon': -118.123,
                  'event_timestamp': datetime.utcnow(),
                  'event_description': 'foo',
                  'event_network': 'us'}
    shake_dict = {'event_id': 'us12345678', 'shakemap_id': 'us12345678', 'shakemap_version': 1,
                  'code_version': '4.5', 'process_timestamp': datetime.utcnow(),
                  'shakemap_originator': 'us', 'map_status': 'RELEASED', 'shakemap_event_type': 'ACTUAL'}
    unc_dict = {'mmi': (1, 1)}
    shakegrid = ShakeGrid(layers, geodict, event_dict, shake_dict, unc_dict)
    shakegrid.save(shakefile)
    popgrid = GMTGrid(popdata, geodict.copy())
    isogrid = GMTGrid(isodata, geodict.copy())
    popgrid.save(popfile)
    isogrid.save(isofile)

    ratedict = {4: {'start': [2010, 2012, 2014, 2016],
                    'end': [2012, 2014, 2016, 2018],
                    'rate': [0.01, 0.02, 0.03, 0.04]},
                156: {'start': [2010, 2012, 2014, 2016],
                      'end': [2012, 2014, 2016, 2018],
                      'rate': [0.02, 0.03, 0.04, 0.05]}}

    popgrowth = PopulationGrowth(ratedict)
    popyear = datetime.utcnow().year
    exposure = Exposure(popfile, popyear, isofile, popgrowth=popgrowth)
    expdict = exposure.calcExposure(shakefile)

    modeldict = [LognormalModel('AF', 11.613073, 0.180683, 1.0),
                 LognormalModel('CN', 10.328811, 0.100058, 1.0)]
    fatmodel = EmpiricalLoss(modeldict)

    # for the purposes of this test, let's override the rates
    # for Afghanistan and China with simpler numbers.
    fatmodel.overrideModel('AF', np.array(
        [0, 0, 0, 0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 0], dtype=np.float32))
    fatmodel.overrideModel('CN', np.array(
        [0, 0, 0, 0, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 0], dtype=np.float32))

    print('Testing very basic fatality calculation...')
    fatdict = fatmodel.getLosses(expdict)
    # strictly speaking, the afghanistant fatalities should be 462,000 but floating point precision dictates otherwise.
    testdict = {'CN': 46111,
                'AF': 461999,
                'TotalFatalities': 508110}
    for key, value in fatdict.items():
        assert value == testdict[key]
    print('Passed very basic fatality calculation...')

    print('Testing grid fatality calculations...')
    mmidata = exposure.getShakeGrid().getLayer('mmi').getData()
    popdata = exposure.getPopulationGrid().getData()
    isodata = exposure.getCountryGrid().getData()
    fatgrid = fatmodel.getLossGrid(mmidata, popdata, isodata)

    assert np.nansum(fatgrid) == 508111
    print('Passed grid fatality calculations...')

    # Testing modifying rates and stuffing them back in...
    chile = LognormalModel('CL', 19.786773, 0.259531, 0.0)
    rates = chile.getLossRates(np.arange(5, 10))
    modrates = rates * 2  # does this make event twice as deadly?

    # roughly the exposures from 2015-9-16 CL event
    expo_pop = np.array(
        [0, 0, 0, 1047000, 7314000, 1789000, 699000, 158000, 0, 0])
    mmirange = np.arange(5, 10)
    chile_deaths = chile.getLosses(expo_pop[4:9], mmirange)
    chile_double_deaths = chile.getLosses(
        expo_pop[4:9], mmirange, rates=modrates)
    print('Chile model fatalities: %f' % chile_deaths)
    print('Chile model x2 fatalities: %f' % chile_double_deaths)


def test():
    homedir = os.path.dirname(os.path.abspath(
        __file__))  # where is this script?
    xmlfile = os.path.join(homedir, '..', 'data', 'fatality.xml')
    ratefile = os.path.join(homedir, '..', 'data',
                            'WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    event = 'northridge'
    shakefile = os.path.join(homedir, '..', 'data',
                             'eventdata', event, '%s_grid.xml' % event)
    popfile = os.path.join(homedir, '..', 'data',
                           'eventdata', event, '%s_gpw.flt' % event)
    isofile = os.path.join(homedir, '..', 'data',
                           'eventdata', event, '%s_isogrid.bil' % event)
    shapefile = os.path.join(homedir, '..', 'data', 'eventdata',
                             event, 'City_BoundariesWGS84', 'City_Boundaries.shp')

    print('Test loading empirical fatality model from XML file...')
    fatmodel = EmpiricalLoss.fromDefaultFatality()
    print('Passed loading empirical fatality model from XML file.')

    print('Test getting alert level from various losses...')
    assert fatmodel.getAlertLevel({'TotalFatalities': 0}) == 'green'
    assert fatmodel.getAlertLevel({'TotalFatalities': 5}) == 'yellow'
    assert fatmodel.getAlertLevel({'TotalFatalities': 100}) == 'orange'
    assert fatmodel.getAlertLevel({'TotalFatalities': 1000}) == 'red'
    # 1000 times Earth's population
    assert fatmodel.getAlertLevel({'TotalFatalities': 1e13}) == 'red'
    print('Passed getting alert level from various losses.')

    print('Test retrieving fatality model data from XML file...')
    model = fatmodel.getModel('af')
    testmodel = LognormalModel('dummy', 11.613073, 0.180683, 8.428822)
    assert model == testmodel
    print('Passed retrieving fatality model data from XML file.')

    print('Testing with known exposures/fatalities for 1994 Northridge EQ...')
    exposure = {'xf': np.array(
        [0, 0, 1506.0, 1946880.0, 6509154.0, 6690236.0, 3405381.0, 1892446.0, 5182.0, 0])}
    fatdict = fatmodel.getLosses(exposure)
    testdict = {'xf': 22}
    assert fatdict['xf'] == testdict['xf']
    print('Passed testing with known exposures/fatalities for 1994 Northridge EQ.')

    print('Testing combining G values from all countries that contributed to losses...')
    fatdict = {'CO': 2.38005147e-01,
               'EC': 8.01285916e+02}
    zetf = fatmodel.getCombinedG(fatdict)
    assert zetf == 2.5
    print('Passed combining G values from all countries that contributed to losses...')

    print('Testing calculating probabilities for standard PAGER ranges...')
    expected = {'UK': 70511, 'TotalFatalities': 70511}
    G = 2.5
    probs = fatmodel.getProbabilities(expected, G)
    testprobs = {'0-1': 3.99586017993e-06,
                 '1-10': 0.00019277654968408576,
                 '10-100': 0.0041568251597835061,
                 '100-1000': 0.039995273501147441,
                 '1000-10000': 0.17297196910604343,
                 '10000-100000': 0.3382545813262674,
                 '100000-10000000': 0.44442457847445394}
    for key, value in probs.items():
        np.testing.assert_almost_equal(value, testprobs[key])
    print('Passed combining G values from all countries that contributed to losses...')

    print('Testing calculating total fatalities for Northridge...')
    expobject = Exposure(popfile, 2012, isofile)
    expdict = expobject.calcExposure(shakefile)
    fatdict = fatmodel.getLosses(expdict)
    testdict = {'XF': 18}
    assert fatdict['XF'] == testdict['XF']
    print('Passed calculating total fatalities for Northridge...')

    print('Testing creating a fatality grid...')
    mmidata = expobject.getShakeGrid().getLayer('mmi').getData()
    popdata = expobject.getPopulationGrid().getData()
    isodata = expobject.getCountryGrid().getData()
    fatgrid = fatmodel.getLossGrid(mmidata, popdata, isodata)
    print(np.nansum(fatgrid))
    print('Passed creating a fatality grid.')

    print('Testing assigning fatalities to polygons...')
    popdict = expobject.getPopulationGrid().getGeoDict()
    shapes = []
    f = fiona.open(shapefile, 'r')
    for row in f:
        shapes.append(row)
    f.close()
    fatshapes, totfat = fatmodel.getLossByShapes(
        mmidata, popdata, isodata, shapes, popdict)
    fatalities = 12
    for shape in fatshapes:
        if shape['id'] == '312':  # Los Angeles
            cname = shape['properties']['CITY_NAME']
            lalosses = shape['properties']['fatalities']
            assert lalosses == fatalities
            assert cname == 'Los Angeles'
            break
    print('Passed assigning fatalities to polygons...')


if __name__ == '__main__':
    lognormal_object_test()
    basic_test()
    test()

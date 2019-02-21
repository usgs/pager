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
import pandas as pd
from mapio.gmt import GMTGrid
from mapio.geodict import GeoDict
from mapio.shake import ShakeGrid

# local imports
from losspager.models.semimodel import get_time_of_day, pop_dist, SemiEmpiricalFatality, URBAN, RURAL, make_test_semi_model


def test_times():
    tday, year, hour = get_time_of_day(
        datetime(2016, 6, 3, 16, 39, 0), -117.6981)
    assert tday == 'transit'
    assert year == 2016
    assert hour == 8

    tday, year, hour = get_time_of_day(
        datetime(2016, 6, 3, 19, 39, 0), -117.6981)
    assert tday == 'day'
    assert year == 2016
    assert hour == 11

    tday, year, hour = get_time_of_day(
        datetime(2016, 6, 4, 7, 39, 0), -117.6981)
    assert tday == 'night'
    assert year == 2016
    assert hour == 23

    tday, year, hour = get_time_of_day(
        datetime(2017, 1, 1, 1, 0, 0), -117.6981)
    assert tday == 'transit'
    assert year == 2016
    assert hour == 17


def test_work():
    popi = 2000
    wforce = pd.Series({'WorkForceTotal': 0.5,
                        'WorkForceAgricultural': 0.5,
                        'WorkForceIndustrial': 0.25,
                        'WorkForceServices': 0.25})
    timeofday = 'day'
    dclass = URBAN
    res, nonres, outdoor = pop_dist(popi, wforce, timeofday, dclass)
    np.testing.assert_almost_equal(res, 410)
    np.testing.assert_almost_equal(nonres, 865)
    np.testing.assert_almost_equal(outdoor, 725)


def test_model_real():
    # test with real data
    popyear = 2012
    homedir = os.path.dirname(os.path.abspath(
        __file__))  # where is this script?
    invfile = os.path.join(homedir, '..', 'data', 'semi_inventory.hdf')
    colfile = os.path.join(homedir, '..', 'data', 'semi_collapse_mmi.hdf')
    fatfile = os.path.join(homedir, '..', 'data', 'semi_casualty.hdf')
    workfile = os.path.join(homedir, '..', 'data', 'semi_workforce.hdf')
    growthfile = os.path.join(homedir, '..', 'data',
                              'WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls')
    popfile = os.path.join(homedir, '..', 'data', 'eventdata',
                           'northridge', 'northridge_gpw.flt')
    shakefile = os.path.join(homedir, '..', 'data',
                             'eventdata', 'northridge', 'northridge_grid.xml')

    isofile = os.path.join(homedir, '..', 'data', 'eventdata',
                           'northridge', 'northridge_isogrid.bil')
    urbanfile = os.path.join(homedir, '..', 'data',
                             'eventdata', 'northridge', 'northridge_urban.bil')
    semi = SemiEmpiricalFatality.fromDefault()
    semi.setGlobalFiles(popfile, popyear, urbanfile, isofile)

    print('Testing semi-empirical losses...')
    losses, resfat, nonresfat = semi.getLosses(shakefile)
    testlosses = 539
    assert testlosses == losses
    print('Passed.')


def test_manual_calcs():
    # where is this script?
    homedir = os.path.dirname(os.path.abspath(__file__))
    popfile = os.path.join(homedir, '..', 'data', 'eventdata',
                           'northridge', 'northridge_gpw.flt')
    urbfile = os.path.join(homedir, '..', 'data', 'eventdata',
                           'northridge', 'northridge_urban.bil')
    isofile = os.path.join(homedir, '..', 'data', 'eventdata',
                           'northridge', 'northridge_isogrid.bil')
    ccode = 'ID'
    timeofday = 'day'
    density = URBAN
    pop = 100000
    mmi = 8.5
    popyear = 2016
    semi = SemiEmpiricalFatality.fromDefault()
    semi.setGlobalFiles(popfile, popyear, urbfile, isofile)

    # let's do the calculations "manually" by getting all of the data and doing our own multiplications
    workforce = semi.getWorkforce(ccode)
    res, nonres, outside = pop_dist(pop, workforce, timeofday, density)
    resinv, nonresinv = semi.getInventories(ccode, density)
    res_collapse = semi.getCollapse(ccode, mmi, resinv)
    nonres_collapse = semi.getCollapse(ccode, mmi, nonresinv)
    res_fat_rates = semi.getFatalityRates(ccode, timeofday, resinv)
    nonres_fat_rates = semi.getFatalityRates(ccode, timeofday, nonresinv)
    res_fats = res * resinv * res_collapse * res_fat_rates
    nonres_fats = nonres * nonresinv * nonres_collapse * nonres_fat_rates
    # print(res_fats)
    # print(nonres_fats)
    fatsum = int(res_fats.sum() + nonres_fats.sum())
    print('Testing that "manual" calculations achieve tested result...')
    assert fatsum == 383
    print('Passed.')


if __name__ == '__main__':
    test_times()
    test_work()
    test_manual_calcs()
    # test_model_single()
    test_model_real()

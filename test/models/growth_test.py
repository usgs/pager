#!/usr/bin/env python

# stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

# third party imports
import numpy as np

# local imports
from losspager.models.growth import PopulationGrowth, adjust_pop

POPURL = 'http://esa.un.org/unpd/wpp/DVD/Files/1_Indicators%20(Standard)/EXCEL_FILES/1_Population/WPP2015_POP_F02_POPULATION_GROWTH_RATE.XLS'


def test_adjust_pop():
    print('Testing simple positive population growth...')
    tpop = 2015
    tevent = 2016
    ccode = 841  # US
    pop = 1e6
    rate = 0.01  # 1% growth rate
    newpop = adjust_pop(pop, tpop, tevent, rate)
    assert newpop == pop + pop * rate
    print('Passed simple positive population growth.')

    print('Testing simple negative population growth...')
    tpop = 2016
    tevent = 2015
    pop = 1e6
    rate = 0.01  # 1% growth rate
    newpop = adjust_pop(pop, tpop, tevent, rate)
    assert newpop == 990099.0  # not (pop - pop*rate) : how come?
    print('Passed simple negative population growth.')

    print('Testing simple zero population growth...')
    tpop = 2016
    tevent = 2016
    pop = 1e6
    rate = 0.01  # 1% growth rate
    newpop = adjust_pop(pop, tpop, tevent, rate)
    assert newpop == pop
    print('Passed simple zero population growth.')


def test_pop_growth():
    homedir = os.path.dirname(os.path.abspath(
        __file__))  # where is this script?
    print('Testing loading Population Growth from UN spreadsheet...')
    pg = PopulationGrowth.fromDefault()
    print('Passed loading Population Growth from UN spreadsheet...')

    print('Testing getting growth rates for the US...')
    rate = pg.getRate(840, 1963)
    assert rate == 1.373 / 100.0
    allrates = np.array([1.581, 1.724, 1.373, 0.987, 0.885, 0.948,
                         0.945, 0.985, 1.035, 1.211, 0.915, 0.907, 0.754]) / 100.0
    starts, usrates = pg.getRates(840)
    np.testing.assert_almost_equal(usrates, allrates)
    print('Passed getting growth rate for the US...')

    # three scenarios to test with regards to population growth rates
    # 1: time population data was "collected" is before the event time
    tpop = 2015
    tevent = 2016
    ccode = 840  # US
    pop = 1e6
    newpop = pg.adjustPopulation(pop, ccode, tpop, tevent)

    tpop = 2007
    tevent = 2016
    ccode = 840
    pop = 1e6
    # TODO:  hand-verify this result!
    newpop = pg.adjustPopulation(pop, ccode, tpop, tevent)

    # #2: time population data was "collected" is after the event time
    tpop = 2016
    tevent = 2012
    ccode = 840  # US
    pop = 1e6
    newpop = pg.adjustPopulation(pop, ccode, tpop, tevent)
    # #3 time population data was collected is equal to event time
    # tpop = 2012
    # tevent = 2012
    # ccode = 841 #US
    # pop = 1e6
    # newpop = pg.adjustPopulation(pop,ccode,tpop,tevent)


if __name__ == '__main__':
    test_adjust_pop()
    test_pop_growth()

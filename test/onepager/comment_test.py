#!/usr/bin/env python

# stdlib imports
import os.path
import sys

# third party imports
import numpy as np
from impactutils.textformat.text import commify

# local imports
from losspager.models.semimodel import SemiEmpiricalFatality
from losspager.utils.expocat import ExpoCat
from losspager.onepager.comment import get_impact_comments, get_structure_comment, get_secondary_hazards
from losspager.onepager.comment import get_historical_comment, get_secondary_comment, SEARCH_RADIUS


def test_impact():
    # both impacts are green
    tz_exp = np.array([0, 0, 0, 102302926316, 13976446978,
                       9127080479, 7567231, 0, 0, 0])
    ug_exp = np.array([0, 0, 240215309, 255785480321,
                       33062696103, 1965288263, 0, 0, 0, 0])
    econexp = {'TZ': tz_exp,
               'UG': ug_exp,
               'TotalEconomicExposure': tz_exp + ug_exp}
    fatdict = {'TZ': 0,
               'UG': 0,
               'TotalFatalities': 0}
    ecodict = {'TZ': 283,
               'UG': 262049,
               'TotalDollars': 262332}
    event_year = 2016
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c1 = 'Green alert for shaking-related fatalities and economic losses. There is a low likelihood of casualties and damage.'
    assert impact1 == impact1_c1
    assert impact2 == ''

    # fatalities are yellow
    fatdict = {'TZ': 0,
               'UG': 1,
               'TotalFatalities': 1}
    ecodict = {'TZ': 283,
               'UG': 262049,
               'TotalDollars': 262332}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c2 = 'Yellow alert for shaking-related fatalities. Some casualties are possible and the impact should be relatively localized. Past events with this alert level have required a local or regional level response.'
    impact2_c2 = 'Green alert for economic losses. There is a low likelihood of damage.'
    assert impact1 == impact1_c2
    assert impact2 == impact2_c2

    # fatalities are orange
    fatdict = {'TZ': 0,
               'UG': 101,
               'TotalFatalities': 101}
    ecodict = {'TZ': 283,
               'UG': 262049,
               'TotalDollars': 262332}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c3 = 'Orange alert for shaking-related fatalities. Significant casualties are likely and the disaster is potentially widespread. Past events with this alert level have required a regional or national level response.'
    impact2_c3 = 'Green alert for economic losses. There is a low likelihood of damage.'
    assert impact1 == impact1_c3
    assert impact2 == impact2_c3

    # fatalities are red
    fatdict = {'TZ': 0,
               'UG': 1001,
               'TotalFatalities': 1001}
    ecodict = {'TZ': 283,
               'UG': 262049,
               'TotalDollars': 262332}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c4 = 'Red alert for shaking-related fatalities. High casualties are probable and the disaster is likely widespread. Past events with this alert level have required a national or international level response.'
    impact2_c4 = 'Green alert for economic losses. There is a low likelihood of damage.'
    assert impact1 == impact1_c4
    assert impact2 == impact2_c4

    # econ losses are yellow
    fatdict = {'TZ': 0,
               'UG': 0,
               'TotalFatalities': 0}
    ecodict = {'TZ': 0,
               'UG': 1000001,
               'TotalDollars': 1000001}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Yellow alert for economic losses. Some damage is possible and the impact should be relatively localized. Estimated economic losses are less than 1% of GDP of Uganda. Past events with this alert level have required a local or regional level response.'
    impact2_c5 = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # econ losses are orange
    fatdict = {'TZ': 0,
               'UG': 0,
               'TotalFatalities': 0}
    ecodict = {'TZ': 0,
               'UG': 100e6 + 1,
               'TotalDollars': 100e6 + 1}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Orange alert for economic losses. Significant damage is likely and the disaster is potentially widespread. Estimated economic losses are 0-1% GDP of Uganda. Past events with this alert level have required a regional or national level response.'
    impact2_c5 = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # econ losses are red
    fatdict = {'TZ': 0,
               'UG': 0,
               'TotalFatalities': 0}
    ecodict = {'TZ': 0,
               'UG': 1000e6 + 1,
               'TotalDollars': 1000e6 + 1}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Red alert for economic losses. Extensive damage is probable and the disaster is likely widespread. Estimated economic losses are 1-10% GDP of Uganda.  Past events with this alert level have required a national or international level response.'
    impact2_c5 = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # econ losses are REALLY red
    fatdict = {'TZ': 0,
               'UG': 0,
               'TotalFatalities': 0}
    ecodict = {'TZ': 0,
               'UG': 15e9,
               'TotalDollars': 15e9}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Red alert for economic losses. Extensive damage is probable and the disaster is likely widespread. Estimated economic losses may exceed the GDP of Uganda.  Past events with this alert level have required a national or international level response.'
    impact2_c5 = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # both alerts are yellow
    fatdict = {'TZ': 0,
               'UG': 1,
               'TotalFatalities': 1}
    ecodict = {'TZ': 0,
               'UG': 1e6 + 1,
               'TotalDollars': 1e6 + 1}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Yellow alert for shaking-related fatalities and economic losses. Some casualties and damage are possible and the impact should be relatively localized. Past yellow alerts have required a local or regional level response.'
    impact2_c5 = 'Estimated economic losses are less than 1% of GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # both alerts are orange
    fatdict = {'TZ': 0,
               'UG': 101,
               'TotalFatalities': 101}
    ecodict = {'TZ': 0,
               'UG': 100e6 + 1,
               'TotalDollars': 100e6 + 1}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Orange alert for shaking-related fatalities and economic losses. Significant casualties and damage are likely and the disaster is potentially widespread. Past orange alerts have required a regional or national level response.'
    impact2_c5 = 'Estimated economic losses are 0-1% GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5

    # both alerts are red
    fatdict = {'TZ': 0,
               'UG': 1001,
               'TotalFatalities': 1001}
    ecodict = {'TZ': 0,
               'UG': 1e9 + 1,
               'TotalDollars': 1e9 + 1}
    impact1, impact2 = get_impact_comments(
        fatdict, ecodict, econexp, event_year, 'TZ')
    impact1_c5 = 'Red alert for shaking-related fatalities and economic losses. High casualties and extensive damage are probable and the disaster is likely widespread. Past red alerts have required a national or international response.'
    impact2_c5 = 'Estimated economic losses are 1-10% GDP of Uganda.'
    assert impact1 == impact1_c5
    assert impact2 == impact2_c5


def test_structure():
    resfat = {'IN': {'A1': 434, 'A2': 837},
              'NP': {'UFB': 200, 'W1': 100}}
    nonresfat = {'IN': {'A1': 434, 'A2': 837},
                 'NP': {'UFB': 200, 'W1': 100}}
    semimodel = SemiEmpiricalFatality.fromDefault()
    structure_comment = get_structure_comment(resfat, nonresfat, semimodel)
    cmpstr = 'Overall, the population in this region resides in structures that are vulnerable to earthquake shaking, though resistant structures exist.  The predominant vulnerable building type is adobe block with light roof construction.'
    assert structure_comment == cmpstr


def test_hazards():
    clat = 0.37
    clon = -79.94
    mag = 7.8
    expocat = ExpoCat.fromDefault()
    minicat = expocat.selectByRadius(clat, clon, SEARCH_RADIUS)
    hazards = get_secondary_hazards(minicat, mag)
    comment = get_secondary_comment(clat, clon, mag)
    for hazard in hazards:
        print('Looking for %s in comment string...' % hazard)
        assert comment.find(hazard) > -1


def test_historical():
    clat = 0.37
    clon = -79.94
    expodict = {'EC': [0, 0, 115000, 5238000, 5971000, 2085000, 1760000, 103000, 0, 0],
                'TotalExposure': [0, 0, 115000, 5238000, 5971000, 2085000, 1760000, 103000, 0, 0]}
    fatdict = {'EC': 98,
               'TotalDeaths': 98}
    ccode = 'EC'
    histcomment = get_historical_comment(clat, clon, 7.8, expodict, fatdict)
    expocat = ExpoCat.fromDefault()
    minicat = expocat.selectByRadius(clat, clon, SEARCH_RADIUS)
    df = minicat.getDataFrame()
    df = df.sort_values(
        ['TotalDeaths', 'MaxMMI', 'NumMaxMMI'], ascending=False)
    assert histcomment.find(commify(int(df.iloc[0]['TotalDeaths']))) > -1


if __name__ == '__main__':
    test_hazards()
    test_historical()
    test_structure()
    test_impact()

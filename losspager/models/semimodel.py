#!/usr/bin/env python

# stdlib imports
from datetime import timedelta
import os.path
import logging

# third party imports
import pandas as pd
import numpy as np
from mapio.shake import ShakeGrid
from mapio.reader import read, get_file_geodict

# neic imports
from impactutils.io.container import HDFContainer

# local imports
from .growth import PopulationGrowth
from losspager.utils.country import Country

# constants indicating what values in urban/rural grid stand for
URBAN = 2
RURAL = 1

# constants for determining time of day
DAY_START_HOUR = 10
DAY_END_HOUR = 17
TRANSIT_START_HOUR_MORNING = 5
TRANSIT_END_HOUR_MORNING = 10
TRANSIT_START_HOUR_EVENING = 17
TRANSIT_END_HOUR_EVENING = 22
NIGHT_START_HOUR_EVENING = 22
NIGHT_END_HOUR_EVENING = 24
NIGHT_START_HOUR_MORNING = 0
NIGHT_END_HOUR_MORNING = 5

# US PAGER-specific country codes
EASTERN_US_CCODE = 903
WESTERN_US_CCODE = 904
CALIFORNIA_US_CCODE = 902
US_CCODE = 840

# time of day columns in casualty spreadsheets
TIMES = {'day': 'CasualtyDay',
         'transit': 'CasualtyDay',
         'night': 'CasualtyNight'}


def add_dicts(dict1, dict2):
    """Sum the values of two dictionaries.

    :param dict1:
      Dictionary (possibly empty) containing keys with floating point values.
    :param dict2:
      Dictionary (possibly empty) containing keys with floating point values.
    :returns:
      New dictionary, with all unique keys from dict1/2, and the sum of the 
      values from each key in both dictionaries.
      Example: 
        dict1 = {'W1':60.0,'W2':75.0}
        dict2 = {'W1':40.0,'W2':25.0,'W3':100.0}
        add_dicts(dict1,dict2) => {'W1':100.0,'W2':100.0,'W3':100.0}
    """
    result = {}
    for key, value in dict1.items():
        if key not in result:
            result[key] = value
        else:
            result[key] += value
    for key, value in dict2.items():
        if key not in result:
            result[key] = value
        else:
            result[key] += value
    return result


def pop_dist(popi, workforce, time, dclass):
    """
    Calculate population distribution (residential, non-residential, and outdoor).
    :param popi: 
      Total population.
    :param workforce: 
      Pandas Series containing indices (WorkForceTotal,WorkForceAgricultural,WorkForceIndustrial,WorkForceServices)
    :param time: Time of day ('day','night','transit')
    :param dclass: Density class (URBAN,RURAL)
    :return: Tuple of (residential,non-residential,outdoor) population numbers.
    """
    fwf = workforce.WorkForceTotal
    fagr = workforce.WorkForceAgricultural
    f_ind = workforce.WorkForceIndustrial
    fser = workforce.WorkForceServices
    fnwf = 1 - fwf
    if dclass == URBAN:
       # DAY TIME
        FDRWF = 0.40
        FDRWFI = 0.01
        FDRWFS = 0.01
        FDRWFA = 0.01

        FDNRWFI = 0.89
        FDNRWFS = 0.89
        FDNRWFA = 0.34
        # EDUCATIONAL SERVICES FRACTION NOT ACCOUNTED IN WORKFORCE DIST.
        FDNRSCH = 0.25

        FDOWF = 0.35
        FDOWFI = 0.1
        FDOWFS = 0.1
        FDOWFA = 0.65

        # TRANSIT TIME
        FTRWF = 0.75
        FTRWFI = 0.20
        FTRWFS = 0.25
        FTRWFA = 0.45

        FTNRWFI = 0.25
        FTNRWFS = 0.25
        FTNRWFA = 0.01

        FTOWF = 0.25
        FTOWFI = 0.55
        FTOWFS = 0.50
        FTOWFA = 0.54

        # NIGHT TIME
        FNRWF = 0.999
        FNRWFI = 0.84
        FNRWFS = 0.89
        FNRWFA = 0.998

        FNNRWFI = 0.15
        FNNRWFS = 0.1
        FNNRWFA = 0.001

        FNOWF = 0.001
        FNOWFI = 0.01
        FNOWFS = 0.01
        FNOWFA = 0.001
    else:
        # RURAL
        # DAY TIME
        FDRWF = 0.40
        FDRWFI = 0.05
        FDRWFS = 0.05
        FDRWFA = 0.01

        FDNRWFI = 0.85
        FDNRWFS = 0.85
        FDNRWFA = 0.04
        # EDUCATIONAL SERVICES FRACTION NOT ACCOUNTED IN WORKFORCE DIST.
        FDNRSCH = 0.25

        FDOWF = 0.35
        FDOWFI = 0.1
        FDOWFS = 0.1
        FDOWFA = 0.95

        # TRANSIT TIME
        FTRWF = 0.80
        FTRWFI = 0.10
        FTRWFS = 0.15
        FTRWFA = 0.65

        FTNRWFI = 0.20
        FTNRWFS = 0.20
        FTNRWFA = 0.01

        FTOWF = 0.20
        FTOWFI = 0.70
        FTOWFS = 0.65
        FTOWFA = 0.34

        # NIGHT TIME
        FNRWF = 0.999
        FNRWFI = 0.89
        FNRWFS = 0.89
        FNRWFA = 0.998

        FNNRWFI = 0.1
        FNNRWFS = 0.1
        FNNRWFA = 0.001

        FNOWF = 0.001
        FNOWFI = 0.01
        FNOWFS = 0.01
        FNOWFA = 0.001

    if time == 'day':
        respop = popi * (FDRWF * fnwf
                         + FDRWFI * fwf * f_ind
                         + FDRWFS * fwf * fser
                         + FDRWFA * fwf * fagr)
        nrpop = popi * (FDNRWFI * fwf * f_ind
                        + FDNRWFS * fwf * fser + FDNRWFA * fwf * fagr + FDNRSCH * fnwf)
        outpop = popi * (FDOWF * fnwf
                         + FDOWFI * fwf * f_ind
                         + FDOWFS * fwf * fser
                         + FDOWFA * fwf * fagr)
    elif time == 'transit':
        respop = popi * (FTRWF * fnwf
                         + FTRWFI * fwf * f_ind
                         + FTRWFS * fwf * fser
                         + FTRWFA * fwf * fagr)
        nrpop = popi * (FTNRWFI * fwf * f_ind
                        + FTNRWFS * fwf * fser + FTNRWFA * fwf * fagr)
        outpop = popi * (FTOWF * fnwf
                         + FTOWFI * fwf * f_ind
                         + FTOWFS * fwf * fser
                         + FTOWFA * fwf * fagr)

    elif time == 'night':
        respop = popi * (FNRWF * fnwf
                         + FNRWFI * fwf * f_ind
                         + FNRWFS * fwf * fser
                         + FNRWFA * fwf * fagr)
        nrpop = popi * (FNNRWFI * fwf * f_ind
                        + FNNRWFS * fwf * fser + FNNRWFA * fwf * fagr)
        outpop = popi * (FNOWF * fnwf
                         + FNOWFI * fwf * f_ind
                         + FNOWFS * fwf * fser
                         + FNOWFA * fwf * fagr)

    respop = np.atleast_1d(np.squeeze(respop))
    nrpop = np.atleast_1d(np.squeeze(nrpop))
    outpop = np.atleast_1d(np.squeeze(outpop))
    return (respop, nrpop, outpop)


def load_panel_from_excel(excelfile):
    """Load a pandas Panel object by reading it from an Excel spreadsheet.

    :param excelfile:
      Path to Excel file.
    :returns:
      pandas Panel object.
    """
    paneldict = {}
    xl = pd.ExcelFile(excelfile)
    for sheet in xl.sheet_names:
        frame = pd.read_excel(excelfile, sheet_name=sheet)
        paneldict[sheet] = frame
    panel = pd.Panel(paneldict)
    return panel


def get_time_of_day(dtime, lon):
    """Determine time of day (one of 'day','night', or 'transit'), and event year and hour.

    :param dtime:
      Datetime object, representing event origin time in UTC.
    :param lon:
      Float longitude of earthquake origin.
    :returns:
      Tuple of time of day,local event year, and local event hour
    """
    # inputs datetime in utc, and local longitude
    toffset = lon / 15
    event_time = dtime + timedelta(0, toffset * 3600)
    event_year = event_time.year
    event_hour = event_time.hour
    timeofday = None
    if event_hour >= DAY_START_HOUR and event_hour < DAY_END_HOUR:
        timeofday = 'day'

    transit1 = (event_hour >= TRANSIT_START_HOUR_MORNING and event_hour
                < TRANSIT_END_HOUR_MORNING)
    transit2 = (event_hour >= TRANSIT_START_HOUR_EVENING and event_hour
                < TRANSIT_END_HOUR_EVENING)
    if transit1 or transit2:
        timeofday = 'transit'

    night1 = (event_hour >= NIGHT_START_HOUR_EVENING and event_hour
              <= NIGHT_END_HOUR_EVENING)
    night2 = (event_hour >= NIGHT_START_HOUR_MORNING and event_hour
              <= NIGHT_END_HOUR_MORNING)
    if night1 or night2:
        timeofday = 'night'
    return (timeofday, event_year, event_hour)


class SemiEmpiricalFatality(object):
    def __init__(self, inventory, collapse, casualty, workforce, growth):
        """Create Semi-Empirical Fatality Model object.

        :param inventory:
          HDFContainer, containing DataFrames named: 
           - 'BuildingTypes',
           - 'RuralNonResidential'
           - 'RuralResidential'
           - 'UrbanNonResidential'
           - 'UrbanResidential'

           where BuildingTypes is a Dataframe with columns: 
             - Code: Building Code ('A','S','C1',etc.)
             - ShortDescription:  A short description of building type (i.e, 'adobe block').
             - OperationalDescription: A (sometimes) shorter description of building type.
             - LongDescription: Full description of building type, i.e. 'High-Rise Ductile Reinforced Concrete Moment Frame'
          All other Dataframes have columns:
            - CountryCode: Two letter ISO country code ('US',etc.)
            - CountryName: Name of country.
            - Building Codes, as listed and described in BuildingTypes Dataframe.

        :param collapse:
          HDFContainer, where first index is country (by two-letter country code), columns are: 
            - BuildingCode:  Building code as above.
            - (IMT)_6.0 -> (IMT)_9.0 Columns with collapse rates at each (IMT) interval, where (IMT) could be MMI,PGA,PGV,PSA1.0, etc.

        :param casualty:
          HDFContainer, where first index is country (by two-letter country code), columns are: 
            - BuildingCode:  Building code as above.
            - CasualtyDay:   Casualty rate, given collapse, during the day.
            - CasualtyNight: Casualty rate, given collapse, during the night.

        :param workforce:
          HDFContainer consisting of a single dataframe, where rows are by country, and columns are:
            - CountryCode two letter ISO country code.
            - CountryCode name of country.
            - WorkforceTotal Fraction of the country population in the workforce.
            - WorkforceAgriculture Fraction of the total workforce employed in agriculture.
            - WorkforceIndustrial Fraction of the total workforce employed in industry.
            - WorkforceServices Fraction of the total workforce employed in services.
        :param growth:
          PopulationGrowth object.

        """
        self._inventory = inventory
        self._collapse = collapse
        self._casualty = casualty
        self._workforce = workforce
        self._popgrowth = growth
        self._country = Country()

    @classmethod
    def fromDefault(cls):
        homedir = os.path.dirname(os.path.abspath(
            __file__))  # where is this module?
        inventory_file = os.path.join(
            homedir, '..', 'data', 'semi_inventory.hdf')
        collapse_file = os.path.join(
            homedir, '..', 'data', 'semi_collapse_mmi.hdf')
        casualty_file = os.path.join(
            homedir, '..', 'data', 'semi_casualty.hdf')
        workforce_file = os.path.join(
            homedir, '..', 'data', 'semi_workforce.hdf')
        return cls.fromFiles(inventory_file, collapse_file, casualty_file, workforce_file)

    @classmethod
    def fromFiles(cls, inventory_file, collapse_file, casualty_file, workforce_file):
        """Create SemiEmpiricalFatality object from a number of input files.

        :param inventory_file:
          HDF5 file containing Semi-Empirical building inventory data in an HDFContainer. (described in __init__).
        :param collapse_file:
          HDF5 file containing Semi-Empirical collapse rate data  in an HDFContainer. (described in __init__).
        :param casualty_file:
          HDF5 file containing Semi-Empirical casualty rate data in an HDFContainer.(described in __init__).
        :param workforce_file:
          HDF5 file containing Semi-Empirical workforce data in an HDFContainer. (described in __init__).
        :param growth_file:
          Excel spreadsheet containing population growth rate data (described in PopulationGrowth.fromUNSpreadsheet()).
        :returns:
          SemiEmpiricalFatality object.
        """
        # turn the inventory,collapse, and casualty spreadsheets into Panels...
        inventory = HDFContainer.load(inventory_file)
        collapse = HDFContainer.load(collapse_file)
        casualty = HDFContainer.load(casualty_file)
        workforce = HDFContainer.load(workforce_file)
        # extract the one dataframe from the Panel
        workforce = workforce.getDataFrame('Workforce')
        workforce = workforce.set_index('CountryCode')

        # read the growth spreadsheet into a PopulationGrowth object...
        popgrowth = PopulationGrowth.fromDefault()

        return cls(inventory, collapse, casualty, workforce, popgrowth)

    def setGlobalFiles(self, popfile, popyear, urbanfile, isofile):
        """Set the global data files (population,urban/rural, country code) for use of model with ShakeMaps.

        :param popfile:
          File name of population grid.
        :param popyear:
          Year population data was collected.
        :param urbanfile:
          File name of urban/rural grid (rural cells indicated with a 1, urban cells with a 2).
        :param isofile:
          File name of numeric ISO country code grid.
        :returns: 
          None
        """
        self._popfile = popfile
        self._popyear = popyear
        self._urbanfile = urbanfile
        self._isofile = isofile

    def getBuildingDesc(self, btype, desctype='short'):
        """Get a building description given a short building type code.

        :param btype:
          Short building type code ('A' (adobe), 'C' (reinforced concrete), etc.)
        :param desctype:
          A string, one of:
            - 'short': Very short descriptions ('adobe block')
            - 'operational': Short description, intended for use in automatically generated sentences about building types.
            - 'long': Most verbose description ('Adobe block (unbaked dried mud block) walls')

        :returns:
          Either a short, operational, or long description of building types.
        """
        bsheet = self._inventory.getDataFrame('BuildingTypes')
        bsheet = bsheet.set_index('Code')
        row = bsheet.loc[btype]
        if desctype == 'short':
            return row['ShortDescription']
        elif desctype == 'operational':
            return row['OperationalDescription']
        else:
            return row['LongDescription']
        return None

    def getWorkforce(self, ccode):
        """Get the workforce data corresponding to a given country code.
        :param ccode:
          Two letter ISO country code.
        :returns:
          Pandas series containing Workforce data for given country 
            (WorkForceTotal,WorkForceAgriculture,WorkForceIndustrial,WorkForceServices)
        """
        try:
            wforce = self._workforce.loc[ccode]
        except:
            wforce = None
        return wforce

    def getCollapse(self, ccode, mmi, inventory):
        """Return the collapse rates for a given country,intensity, and inventory.

        :param ccode:
          Two letter ISO country code.
        :param mmi:
          MMI value (one of 6.0,6.5,7.0,7.5,8.0,8.5,9.0)
        :param inventory:
          Pandas Series containing an inventory for the given country.
        :returns:
          Pandas Series object containing the collapse rates for given building types, ccode, and MMI.
        """
        collapse_frame = self._collapse.getDataFrame(ccode)
        collapse_frame = collapse_frame.set_index('BuildingCode')
        try:
            idx = inventory.index.drop('Unnamed: 0')
            collapse_frame = collapse_frame.loc[idx]
        except Exception:
            collapse_dict = inventory.to_dict()
            collapse = pd.Series(collapse_dict)
            for key, value in collapse_dict.items():
                collapse[key] = np.nan
            return collapse
        mmicol = 'MMI_%s' % str(mmi)
        collapse = collapse_frame[mmicol]
        return collapse

    def getFatalityRates(self, ccode, timeofday, inventory):
        """Return fatality rates for a given country, time of day, and inventory.

        :param ccode:
          Two-letter ISO country code.
        :param timeofday:
          One of 'day','transit', or 'night'.
        :param inventory:
          Pandas Series containing an inventory for the given country.
        :returns:
          Pandas Series object containing fatality rates for given country, time of day, and inventory.
        """
        fatalframe = self._casualty.getDataFrame(ccode)
        fatalframe = fatalframe.set_index('BuildingCode')
        timecol = TIMES[timeofday]
        if 'Unnamed: 0' in inventory.index:
            idx = inventory.index.drop('Unnamed: 0')
        else:
            idx = inventory.index
        fatrates = fatalframe.loc[idx][timecol]
        return fatrates

    def getInventories(self, ccode, density):
        """Return two pandas Series objects corresponding to the urban or rural inventory for given country.

        :param ccode:
          Two-letter ISO country code.
        :param density:
          One of semimodel.URBAN (2) or semimodel.RURAL (1).
        :returns:
          Two Pandas Series: 1) Residential Inventory and 2) Non-Residential Inventory.
        """
        if density == URBAN:
            resinv = self._inventory.getDataFrame('UrbanResidential')
            nresinv = self._inventory.getDataFrame('UrbanNonResidential')
        else:
            resinv = self._inventory.getDataFrame('RuralResidential')
            nresinv = self._inventory.getDataFrame('RuralNonResidential')
        resinv = resinv.set_index('CountryCode')
        nresinv = nresinv.set_index('CountryCode')

        # we may be missing inventory for certain countries (Bonaire?). Return empty series.
        if ccode not in resinv.index or ccode not in nresinv.index:
            return (pd.Series(), pd.Series())

        # pandas series of residential inventory
        resrow = resinv.loc[ccode]
        resrow = resrow.drop('CountryName')
        # pandas series of non-residential inventory
        nresrow = nresinv.loc[ccode]
        nresrow = nresrow.drop('CountryName')

        # now trim down the series to only include finite and non-zero values
        resrow = resrow[resrow.notnull()]
        resrow = resrow[resrow > 0]
        nresrow = nresrow[nresrow.notnull()]
        nresrow = nresrow[nresrow > 0]

        return (resrow, nresrow)

    def getLosses(self, shakefile):
        """Calculate number of fatalities using semi-empirical approach.

        :param shakefile:
          Path to a ShakeMap grid.xml file.
        :returns:
          Tuple of:
            1) Total number of fatalities
            2) Dictionary of residential fatalities per building type, per country.
            3) Dictionary of non-residential fatalities per building type, per country.
        """
        # get shakemap geodict
        shakedict = ShakeGrid.getFileGeoDict(shakefile, adjust='res')
        # get population geodict
        popdict = get_file_geodict(self._popfile)

        # get country code geodict
        isodict = get_file_geodict(self._isofile)

        # get urban grid geodict
        urbdict = get_file_geodict(self._urbanfile)

        # load all of the grids we need
        if popdict == shakedict == isodict == urbdict:
            # special case, probably for testing...
            shakegrid = ShakeGrid.load(shakefile, adjust='res')
            popgrid = read(self._popfile)
            isogrid = read(self._isofile)
            urbgrid = read(self._urbanfile)
        else:
            sampledict = popdict.getBoundsWithin(shakedict)
            shakegrid = ShakeGrid.load(shakefile,
                                       samplegeodict=sampledict,
                                       resample=True,
                                       method='linear',
                                       adjust='res')
            popgrid = read(self._popfile,
                           samplegeodict=sampledict,
                           resample=False)
            isogrid = read(self._isofile,
                           samplegeodict=sampledict,
                           resample=True,
                           method='nearest',
                           doPadding=True,
                           padValue=0)
            urbgrid = read(self._urbanfile,
                           samplegeodict=sampledict,
                           resample=True,
                           method='nearest',
                           doPadding=True,
                           padValue=RURAL)

        # determine the local apparent time of day (based on longitude)
        edict = shakegrid.getEventDict()
        etime = edict['event_timestamp']
        elon = edict['lon']
        time_of_day, event_year, event_hour = get_time_of_day(etime, elon)

        # round off our MMI data to nearest 0.5 (5.5 should stay 5.5, 5.4
        # should become 5.5, 5.24 should become 5.0, etc.)
        # TODO:  Someday, make this more general to include perhaps grids of all IMT values, or
        # at least the ones we have collapse data for.
        mmidata = np.round(shakegrid.getLayer('mmi').getData() / 0.5) * 0.5

        # get arrays from our other grids
        popdata = popgrid.getData()
        isodata = isogrid.getData()
        urbdata = urbgrid.getData()

        # modify the population values for growth rate by country
        ucodes = np.unique(isodata[~np.isnan(isodata)])
        for ccode in ucodes:
            cidx = (isodata == ccode)
            popdata[cidx] = self._popgrowth.adjustPopulation(
                popdata[cidx], ccode, self._popyear, event_year)

        # create a dictionary containing indoor populations by building type (in cells where MMI >= 6)
        #popbystruct = get_indoor_pop(mmidata,popdata,urbdata,isodata,time_of_day)

        # find all mmi values greater than 9, set them to 9
        mmidata[mmidata > 9.0] = 9.0

        # dictionary containers for sums of fatalities (res/nonres) by building type
        res_fatal_by_ccode = {}
        nonres_fatal_by_ccode = {}

        # fatality sum
        ntotal = 0

        # loop over countries
        ucodes = np.unique(isodata[~np.isnan(isodata)])
        for ucode in ucodes:
            if ucode == 0:
                continue
            res_fatal_by_btype = {}
            nonres_fatal_by_btype = {}

            cdict = self._country.getCountry(int(ucode))
            ccode = cdict['ISO2']
            # get the workforce Series data for the current country
            wforce = self.getWorkforce(ccode)
            if wforce is None:
                logging.info('No workforce data for %s.  Skipping.' %
                             (cdict['Name']))
                continue

            # loop over MMI values 6-9
            for mmi in np.arange(6, 9.5, 0.5):
                c1 = (mmidata == mmi)
                c2 = (isodata == ucode)
                if ucode > 900 and ucode != CALIFORNIA_US_CCODE:
                    ucode = US_CCODE
                for dclass in [URBAN, RURAL]:
                    c3 = (urbdata == dclass)

                    # get the population data in those cells at MMI, in country, and density class
                    # I think I want an AND condition here
                    popcells = popdata[c1 & c2 & c3]

                    # get the population distribution across residential, non-residential, and outdoor.
                    res, nonres, outside = pop_dist(
                        popcells, wforce, time_of_day, dclass)

                    # get the inventory for urban residential
                    resrow, nresrow = self.getInventories(ccode, dclass)

                    # TODO - figure out why this is happening, make the following lines
                    # not necessary
                    if 'Unnamed: 0' in resrow:
                        resrow = resrow.drop('Unnamed: 0')
                    if 'Unnamed: 0' in nresrow:
                        nresrow = nresrow.drop('Unnamed: 0')
                    # now multiply the residential/non-residential population through the inventory data
                    numres = len(resrow)
                    numnonres = len(nresrow)
                    resmat = np.reshape(
                        resrow.values, (numres, 1)).astype(np.float32)
                    nresmat = np.reshape(
                        nresrow.values, (numnonres, 1)).astype(np.float32)
                    popres = np.tile(res, (numres, 1))
                    popnonres = np.tile(nonres, (numnonres, 1))
                    popresbuilding = (popres * resmat)
                    popnonresbuilding = (popnonres * nresmat)

                    # now we have the residential and non-residental population
                    # distributed through the building types for each cell that matches
                    # MMI,country, and density criteria.
                    # popresbuilding rows are building types, columns are population cells

                    # next, we get the collapse rates for these buildings
                    # and multiply them by the population by building.
                    collapse_res = self.getCollapse(ccode, mmi, resrow)
                    collapse_nonres = self.getCollapse(ccode, mmi, nresrow)
                    resrates = np.reshape(
                        collapse_res.values.astype(np.float32), (numres, 1))
                    nonresrates = np.reshape(
                        collapse_nonres.values.astype(np.float32), (numnonres, 1))
                    rescollapse = popresbuilding * resrates
                    nonrescollapse = popnonresbuilding * nonresrates

                    # get the fatality rates given collapse by building type and
                    # multiply through the result of collapse*population per building
                    resfatalcol = self.getFatalityRates(
                        ccode, time_of_day, resrow)
                    nonresfatalcol = self.getFatalityRates(
                        ccode, time_of_day, nresrow)
                    resfatal = np.reshape(
                        resfatalcol.values.astype(np.float32), (numres, 1))
                    nonresfatal = np.reshape(
                        nonresfatalcol.values.astype(np.float32), (numnonres, 1))
                    resfat = rescollapse * resfatal
                    nonresfat = nonrescollapse * nonresfatal

                    # zero out the cells where fatalities are less than 1 or nan
                    try:
                        if len(resfat) and len(resfat[0]):
                            resfat[np.ma.masked_less(resfat, 1).mask] = 0.0
                    except:
                        resfat[np.isnan(resfat)] = 0.0
                    try:
                        if len(nonresfat) and len(nonresfat[0]):
                            nonresfat[np.ma.masked_less(
                                nonresfat, 1).mask] = 0.0
                    except:
                        nonresfat[np.isnan(nonresfat)] = 0.0

                    # sum the fatalities per building through all cells
                    resfatbybuilding = np.nansum(resfat, axis=1)
                    nonresfatbybuilding = np.nansum(nonresfat, axis=1)
                    resfdict = dict(
                        zip(resrow.index, resfatbybuilding.tolist()))
                    nonresfdict = dict(
                        zip(nresrow.index, nonresfatbybuilding.tolist()))
                    res_fatal_by_btype = add_dicts(
                        res_fatal_by_btype, resfdict)
                    nonres_fatal_by_btype = add_dicts(
                        nonres_fatal_by_btype, nonresfdict)

            # add the fatalities by building type to the dictionary containing fatalities by country
            res_fatal_by_ccode[ccode] = res_fatal_by_btype.copy()
            nonres_fatal_by_ccode[ccode] = nonres_fatal_by_btype.copy()

            # increment the total number of fatalities
            ntotal += int(sum(res_fatal_by_btype.values())
                          + sum(nonres_fatal_by_btype.values()))

        return (ntotal, res_fatal_by_ccode, nonres_fatal_by_ccode)

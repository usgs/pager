#!/usr/bin/env python

#stdlib
import time
import warnings

#third party
import numpy as np
from mapio.gmt import GMTGrid
from mapio.gdal import GDALGrid
from mapio.shake import ShakeGrid
from mapio.geodict import GeoDict

#local imports
from losspager.utils.exception import PagerException
from losspager.utils.country import Country
from losspager.utils.ftype import get_file_type
from .growth import PopulationGrowth

SCENARIO_WARNING = 10 #number of years after date of population data to issue a warning
SCENARIO_ERROR = 20 #number of years after date of population data to raise an exception

def calc_exposure(mmidata,popdata,isodata):
    """Calculate population exposure to shaking per country.

    :param mmidata:
      Scalar or array-like value containing floating point MMI data values (range 1-10).
    :param popdata:
      Scalar or array-like value containing integer population data values.
    :param isodata:
      Scalar or array-like value containing integer country-code (ISO 3166-1 numeric) data values.
    :returns:
      Dictionary of population exposures to shaking, keys are country code, values are 10-element arrays.
    """
    mmidata = np.array(mmidata)
    popdata = np.array(popdata)
    isodata = np.array(isodata)
    exposures = {}
    ccodes = np.unique(isodata)
    for ccode in ccodes:
        cidx = np.ravel_multi_index(np.where(isodata == ccode),isodata.shape)
        expsum = np.zeros((10),dtype=np.uint32)
        for mmi in range(1,11):
            mmi_lower = mmi-0.5
            mmi_upper = mmi+0.5
            midx = np.ravel_multi_index(np.where((mmidata >= mmi_lower) & (mmidata < mmi_upper)),mmidata.shape)
            idx = np.unravel_index(np.intersect1d(cidx,midx),mmidata.shape)
            popsum = np.nansum(popdata[idx])
            expsum[mmi-1] = int(popsum)
        exposures[ccode] = expsum[:]

    return exposures

class Exposure(object):
    def __init__(self,popfile,popyear,isofile,popgrowth=None):
        """Create Exposure object, with population and country code grid files,
        and a dictionary of country growth rates.

        :param popfile:
          Any GMT or ESRI style grid file supported by MapIO, containing population data.
        :param popyear:
          Integer indicating year when population data is valid.
        :param isofile:
          Any GMT or ESRI style grid file supported by MapIO, containing country code data (ISO 3166-1 numeric).
        """
        self._popfile = popfile
        self._popyear = popyear
        self._isofile = isofile
        self._popgrid = None
        self._isogrid = None
        self._shakegrid = None
        if popgrowth is not None:
            self._popgrowth = popgrowth
        else:
            self._popgrowth = PopulationGrowth.fromDefault()
        self._country = Country()
        self._pop_class = get_file_type(self._popfile)
        self._iso_class = get_file_type(self._isofile)
        
    def calcExposure(self,shakefile):
        """Calculate population exposure to shaking, per country, plus total exposure across all countries.

        :param shakefile:
          Path to ShakeMap grid.xml file.
        :returns:
          Dictionary containing country code (ISO2) keys, and values of
          10 element arrays representing population exposure to MMI 1-10.
          Dictionary will contain an additional key 'Total', with value of exposure across all countries.
        """
        #get shakemap geodict
        shakedict = ShakeGrid.getFileGeoDict(shakefile,adjust='res')
            
        #get population geodict
        popdict,t = self._pop_class.getFileGeoDict(self._popfile)

        #get country code geodict
        isodict,t = self._iso_class.getFileGeoDict(self._isofile)

        #special case for very high latitude events that may be outside the bounds
        #of our population data...
        if not popdict.intersects(shakedict):
            expdict = {'UK':np.zeros((10,)),'TotalExposure':np.zeros((10,))}
            return expdict
        
        if popdict == shakedict == isodict:
            #special case, probably for testing...
            self._shakegrid = ShakeGrid.load(shakefile,adjust='res')
            self._popgrid = self._pop_class.load(self._popfile)
            self._isogrid = self._iso_class.load(self._isofile)
        else:
            sampledict = popdict.getBoundsWithin(shakedict)
            self._shakegrid = ShakeGrid.load(shakefile,samplegeodict=sampledict,resample=True,
                                             method='linear',adjust='res')
            self._popgrid = self._pop_class.load(self._popfile,samplegeodict=sampledict,
                                                 resample=False,doPadding=True,padValue=np.nan)
            self._isogrid = self._iso_class.load(self._isofile,samplegeodict=sampledict,
                                                 resample=True,method='nearest',doPadding=True,padValue=0)

        mmidata = self._shakegrid.getLayer('mmi').getData()
        popdata = self._popgrid.getData()
        isodata = self._isogrid.getData()

        eventyear = self._shakegrid.getEventDict()['event_timestamp'].year

        #in order to avoid crazy far-future scenarios where PAGER models are probably invalid,
        #check to see if the time gap between the date of population data collection and event year
        #reaches either of a couple of different thresholds.
        if eventyear > self._popyear:
            tdiff = (eventyear - self._popyear)
            if tdiff > SCENARIO_WARNING and tdiff < SCENARIO_ERROR:
                msg = '''The input ShakeMap event year is more than %i years from the population date.
                PAGER results for events this far in the future may not be valid.''' % SCENARIO_WARNING
                warnings.warn(msg)
            if tdiff > SCENARIO_ERROR:
                msg = '''The input ShakeMap event year is more than %i years from the population date.
                PAGER results for events this far in the future are not valid. Stopping.''' % SCENARIO_ERROR
                raise PagerException(msg)
        
        ucodes = np.unique(isodata)
        for ccode in ucodes:
            cidx = (isodata == ccode)
            popdata[cidx] = self._popgrowth.adjustPopulation(popdata[cidx],ccode,self._popyear,eventyear)
        
        exposure_dict = calc_exposure(mmidata,popdata,isodata)
        newdict = {}
        #Get rolled up exposures
        total = np.zeros((10,),dtype=np.uint32)
        for isocode,value in exposure_dict.items():
            cdict = self._country.getCountry(int(isocode))
            if cdict is None:
                ccode = 'UK'
            else:
                ccode = cdict['ISO2']
            newdict[ccode] = value
            total += value

        newdict['TotalExposure'] = total
        return newdict

    def getPopulationGrid(self):
        """Return the internal population grid.

        :returns:
          Population grid.
        """
        if self._popgrid is None:
            raise PagerException('calcExposure() method must be called first.')
        return self._popgrid

    def getCountryGrid(self):
        """Return the Grid2D object containing ISO numeric country codes.

        :returns:
          Grid2D object containing ISO numeric country codes.
        """
        if self._isogrid is None:
            raise PagerException('calcExposure() method must be called first.')
        return self._isogrid

    def getShakeGrid(self):
        """Return the MultiGrid object containing ShakeMap data.

        :returns:
          MultiGrid object containing ShakeMap data.
        """
        if self._shakegrid is None:
            raise PagerException('calcExposure() method must be called first.')
        return self._shakegrid
        

    
        

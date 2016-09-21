#!/usr/bin/env python

#stdlib imports
from xml.dom import minidom
from collections import OrderedDict
import os.path

#third party imports
import numpy as np
from scipy.special import erfc, erfcinv, erf
import shapely
from mapio.grid2d import Grid2D

#local imports
from losspager.utils.country import Country
from losspager.utils.probs import calcEmpiricalProbFromRange
from losspager.utils.exception import PagerException

#TODO: What should these values be?  Mean loss rates for all countries?
DEFAULT_THETA = 16.0
DEFAULT_BETA = 0.15
DEFAULT_L2G = 1.0

class LossModel(object):
    def __init__(self,name,rates,l2g,alpha=None):
        """Create a loss model from an array of loss rates at MMI 1-10.

        :param name:
          Name (usually two letter country code) for model.
        :param rates:
          Array-like float values 10 elements in length.
        :param l2g:
          Float value defining the value of the L2G norm calculated when model was derived.
        :param alpha:
          Float value defining the alpha (economic correction factor) value for the model.  
          Not specified/used for fatality models.
        :returns:
          LossModel instance.
        """
        self._name = name
        self._rates = rates[:]
        self._l2g = l2g
        self._alpha = alpha

    def __repr__(self):
        """return string representation of loss model.
        """
        mmirange = np.arange(5,10)
        rates = self.getLossRates(mmirange)
        reprstr = ''
        for i in range(0,len(mmirange)):
            mmi = mmirange[i]
            rate = rates[i]
            reprstr += 'MMI %i: 1 in %s\n' % (mmi,format(int(1.0/rate),",d"))
        return reprstr
        
    def getLossRates(self,mmirange):
        mmirange = np.array(mmirange)
        idx = mmirange - 1
        return self._rates[idx]

    @property
    def name(self):
        """Return the name associated with this model.
        
        :returns:
          The name associated with this model.
        """
        return self._name
    
    @property
    def theta(self):
        """Return the theta value associated with this model.
        
        :returns:
          The theta associated with this model.
        """
        return self._theta
    
    @property
    def beta(self):
        """Return the beta value associated with this model.
        
        :returns:
          The beta value associated with this model.
        """
        return self._beta

    @property
    def alpha(self):
        """Return the alpha value associated with this model (may be None).
        
        :returns:
          The alpha value associated with this model (may be None).
        """
        return self._alpha

    @property
    def l2g(self):
        """Return the L2G value associated with this model.
        
        :returns:
          The L2G value associated with this model.
        """
        return self._l2g

    def getLosses(self,exp_pop,mmirange,rates=None):
        """Calculate losses given input arrays of population exposures and MMI values.

        :param exp_pop:
          Array of population exposed at mmirange values.
        :param mmirange:
          Array of MMI values exp_pop is exposed to.
        :param rates:
          Array of 10 loss rates which, if specified, will be used instead of the lognormal rates.
        :returns:
          Scalar floating point number of losses.
        """
        if rates is None:
            rates = self.getLossRates(mmirange)
        deaths = np.nansum(rates*exp_pop)
        return deaths

    def getArea(self):
        """Calculate the area under the loss rate curve (defined for MMI 5-9).

        Used internally for model to model comparisons.

        :returns:
          Area under the loss rate curve (defined for MMI 1-10).
        """
        mmirange = np.arange(5,10)
        rates = self.getLossRates(mmirange)
        area = np.trapz(rates,mmirange)
        return area

    def __lt__(self,other):
        """Is this model less deadly than other model?

        :param other:
          Another LognormalModel instance.
        :returns:
          True if this model is less deadly than other model.
        """
        area1 = self.getArea()
        area2 = other.getArea()
        if area1 < area2:
            return True

    def __le__(self,other):
        """Is this model less than or just as deadly as other model?

        :param other:
          Another LognormalModel instance.
        :returns:
          True if this model is less than or just as deadly as other model.
        """
        area1 = self.getArea()
        area2 = other.getArea()
        if area1 <= area2:
            return True

    def __eq__(self,other):
        """Is this model equally deadly as other model?

        :param other:
          Another LognormalModel instance.
        :returns:
          True if this model is equally deadly as other model.
        """
        area1 = self.getArea()
        area2 = other.getArea()
        if area1 == area2:
            return True

    def __gt__(self,other):
        """Is this model more deadly than other model?

        :param other:
          Another LognormalModel instance.
        :returns:
          True if this model is more deadly than other model.
        """
        area1 = self.getArea()
        area2 = other.getArea()
        if area1 > area2:
            return True

    def __ge__(self,other):
        """Is this model greater than or just as deadly as other model?

        :param other:
          Another LognormalModel instance.
        :returns:
          True if this model is greater than or just as deadly as other model.
        """
        area1 = self.getArea()
        area2 = other.getArea()
        if area1 >= area2:
            return True
    
class LoglinearModel(LossModel):
    """Loglinear loss model (defined by theta/beta (or mu/sigma) values.
    """
    def __init__(self,name,theta,beta,l2g,alpha=None):
        """Instantiate Loglinear Loss object.

        :param name:
          Name (usually two letter country code) for model.
        :param theta:
          Float value defining the theta (or mu) value for the model.
        :param beta:
          Float value defining the beta (or sigma) value for the model.
        :param l2g:
          Float value defining the value of the L2G norm calculated when model was derived.
        :param alpha:
          Float value defining the alpha (economic correction factor) value for the model.  
          Not specified/used for fatality models.
        :returns:
          LognormalModel instance.
        """
        self._name = name
        self._theta = theta
        self._beta = beta
        self._l2g = l2g
        self._alpha = alpha

    def getLossRates(self,mmirange):
        """Get the loss rates at each of input MMI values.

        :param mmirange:
          Array-like range of MMI values at which loss rates will be calculated.
        :returns:
          Array of loss rates for input MMI values.
        """
        mmi = np.array(mmirange)
        yy = numpy.power(10,(theta - (mmi*beta)))
        return yy    
    
class LognormalModel(LossModel):
    """Lognormal loss model (defined by theta/beta (or mu/sigma) values.
    """
    def __init__(self,name,theta,beta,l2g,alpha=None):
        """Instantiate Lognormal Loss object.

        :param name:
          Name (usually two letter country code) for model.
        :param theta:
          Float value defining the theta (or mu) value for the model.
        :param beta:
          Float value defining the beta (or sigma) value for the model.
        :param l2g:
          Float value defining the value of the L2G norm calculated when model was derived.
        :param alpha:
          Float value defining the alpha (economic correction factor) value for the model.  
          Not specified/used for fatality models.
        :returns:
          LognormalModel instance.
        """
        self._name = name
        self._theta = theta
        self._beta = beta
        self._l2g = l2g
        self._alpha = alpha

    def getLossRates(self,mmirange):
        """Get the loss rates at each of input MMI values.

        :param mmirange:
          Array-like range of MMI values at which loss rates will be calculated.
        :returns:
          Array of loss rates for input MMI values.
        """
        mmi = np.array(mmirange)
        xx = np.log(mmirange/self._theta)/self._beta
        yy = 0.5*erfc(-xx/np.sqrt(2))
        return yy

class EmpiricalLoss(object):
    """Container class for multiple LognormalModel objects.
    """
    def __init__(self,model_list,losstype='fatality'):
        """Instantiate EmpiricalLoss class.

        :param model_list:
          List of LognormalModel objects.  The names of these will be used as keys for the getModel() method.
        :param losstype:
          One of 'fatality' or 'economic'.
        :returns:
          EmpiricalLoss instance.
        """
        if losstype not in ['fatality','economic']:
            raise PagerException('losstype must be one of ("fatality","economic").')
        self._loss_type = losstype
        self._model_dict = {}
        for model in model_list:
            self._model_dict[model.name] = model
        self._country = Country() #object that can translate between different ISO country representations.
        self._overrides = {} #dictionary of manually set rates (not necessarily lognormal)

    def getModel(self,ccode):
        """Return the LognormalModel associated with given country code, 
        or a default model if country code not found.

        :param ccode:
          Usually two letter ISO country code.
        :returns:
          LognormalModel instance containing model for input country code, or a default model.
        """
        ccode = ccode.upper()
        default = LognormalModel('default',DEFAULT_THETA,DEFAULT_BETA,DEFAULT_L2G)
        if ccode in self._model_dict:
            return self._model_dict[ccode]
        else:
            return default

    @classmethod
    def fromDefaultFatality(cls):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this module?
        fatxml = os.path.join(homedir,'..','data','fatality.xml')
        return cls.fromXML(fatxml)

    @classmethod
    def fromDefaultEconomic(cls):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this module?
        econxml = os.path.join(homedir,'..','data','economy.xml')
        return cls.fromXML(econxml)
        
    @classmethod
    def fromXML(cls,xmlfile):
        """Load country-specific models from an XML file of the form:
          <?xml version="1.0" encoding="US-ASCII" standalone="yes"?>
          
          <models vstr="2.2" type="fatality">
          
            <model ccode="AF" theta="11.613073" beta="0.180683" gnormvalue="1.0"/>
            
          </models>

          or 

          <?xml version="1.0" encoding="US-ASCII" standalone="yes"?>
          
          <models vstr="1.3" type="economic">
          
            <model alpha="15.065400" beta="0.100000" gnormvalue="4.113200" ccode="AF"/>
            
          </models>
        
        :param xmlfile:
          XML file containing model parameters (see above).
        :returns:
          EmpiricalLoss instance.
        """
        root = minidom.parse(xmlfile)
        rootmodels = root.getElementsByTagName('models')[0]
        models = rootmodels.getElementsByTagName('model')
        losstype = rootmodels.getAttribute('type')
        model_list = []
        for model in models:
            key = model.getAttribute('ccode')
            theta = float(model.getAttribute('theta'))
            beta = float(model.getAttribute('beta'))
            l2g = float(model.getAttribute('gnormvalue'))
            if model.hasAttribute('alpha'):
                alpha = float(model.getAttribute('alpha'))
            else:
                alpha = None
            model_list.append(LognormalModel(key,theta,beta,l2g,alpha=alpha))
        root.unlink()

        return cls(model_list,losstype)

    def getLossRates(self,ccode,mmirange):
        """Return loss rates for given country country code model at input MMI values.

        :param ccode:
          Country code (usually two letter ISO code).
        :param mmirange:
          Array-like range of MMI values at which loss rates will be calculated.
        :returns:
          Rates from LognormalModel associated with ccode, or default model (see getModel()).
        """
        #mmirange is mmi value, not index
        model = self.getModel(ccode)
        yy = model.getLossRates(mmirange)
        return yy
    
    def getLosses(self,exposure_dict):
        """Given an input dictionary of ccode (usually ISO numeric), calculate losses per country and total losses.

        :param exposure_dict:
          Dictionary containing country code keys, and 10 element arrays representing population
          exposures to shaking from MMI values 1-10.  If loss type is economic, then this 
          input represents exposure *x* per capita GDP *x* alpha (a correction factor).
        :returns:
          Dictionary containing country code keys and integer population estimations of loss.
        """
        #Get a loss dictionary
        fatdict = {}
        for ccode,exparray in exposure_dict.items():
            if ccode.find('Total') > -1: #exposure array will now also have a row of Total Exposure to shaking.
                continue
            if ccode == 'UK': #unknown
                continue
            mmirange = np.arange(5,10)
            model = self.getModel(ccode)
            if ccode in self._overrides:
                rates = self.getOverrideModel(ccode)[4:9]
            else:
                rates = None

            expo = exparray[:]
            expo[8] += expo[9]
            expo = expo[4:9] #should now be the same size as rates array
            losses = model.getLosses(expo,mmirange,rates=rates)
            fatdict[ccode] = int(losses) #TODO: int or round, or neither?

        #now go through the whole list, and get the total number of losses.
        total = sum(list(fatdict.values()))
        if self._loss_type == 'fatality':
            fatdict['TotalFatalities'] = total
        else:
            fatdict['TotalDollars'] = total
        return fatdict

    def getCombinedG(self,lossdict):
        """Get combined L2G statistic for all countries contributing to losses.

        :param lossdict:
          Dictionary (as retued by getLosses() method, containing keys of ISO2 country codes, 
          and values of loss (fatalities or dollars) for that country.
        :returns:
          sqrt(sum(l2g^2)) for array of all l2g values from countries that had non-zero losses.
        """
        #combine g norm values from all countries that contributed to losses, or if NO losses in
        #any countries, then the combined G from all of them.
        g = []
        has_loss = np.sum(list(lossdict.values())) > 0
        for ccode,loss in lossdict.items():
            if has_loss:
                if loss > 0:
                    g.append(self.getModel(ccode).l2g)
            else:
                g.append(self.getModel(ccode).l2g)
            
        g = np.array(g)
        zetf = np.sqrt(np.sum(np.power(g,2)))
        if zetf > 2.5:
            zetf = 2.5
        return zetf

    def getProbabilities(self,lossdict,G):
        """Calculate probabilities over the standard PAGER loss ranges.

        :param lossdict:
          Dictionary (as retued by getLosses() method, containing keys of ISO2 country codes, 
          and values of loss (fatalities or dollars) for that country.
        :param G:
          Combined G value (see getCombinedG() method).
        :returns:
          Ordered Dictionary of probability of losses over ranges : 
           - '0-1' (green alert)
           - '1-10' (yellow alert)
           - '10-100' (yellow alert)
           - '100-1000' (orange alert)
           - '1000-10000' (red alert)
           - '10000-100000' (red alert)
           - '100000-10000000' (red alert)
        """
        ranges = OrderedDict([('0-1',0.0),
                              ('1-10',0.0),
                              ('10-100',0.0),
                              ('100-1000',0.0),
                              ('1000-10000',0.0),
                              ('10000-100000',0.0),
                              ('100000-10000000',0.0)])
        expected = np.sum(list(lossdict.values()))
        if self._loss_type == 'economic':
            expected = expected / 1e6 #turn USD into millions of USD
        for rangekey,value in ranges.items():
            rparts = rangekey.split('-')
            rmin = int(rparts[0])
            if len(rparts) == 1:
                rmax = int(rparts[0])
            else:
                rmax = int(rparts[1])
                #the high end of the highest red range should be a very large number (ideally infinity).
                #one trillion should do it. 
                if rmax == 10000000:
                    rmax = 1e12
            prob = calcEmpiricalProbFromRange(G,expected,(rmin,rmax))
            ranges[rangekey] = prob
        return ranges

    def getAlertLevel(self,lossdict):
        """Get the alert level associated with the input losses.

        :param lossdict:
          Loss results dictionary as returned by getLosses() method.
        :returns:
          String alert level, one of ('green','yellow','orange','red').
        """
        levels = [(1,'green'),(100,'yellow'),(1000,'orange'),(1e12,'red')]
        if 'TotalFatalities' in lossdict:
            total = lossdict['TotalFatalities']
        else:
            total = lossdict['TotalDollars']/1e6
        for i in range(0,len(levels)-1):
            lossmax,thislevel = levels[i]
            if total < lossmax:
                return thislevel
        return 'red' #we should never get here, unless we have 1e18 USD in losses!
    
    def overrideModel(self,ccode,rates):
        """Override the rates determined from theta,beta values with these hard-coded ones.
        Once set on the instance object, these will be the preferred rates.

        NB: While probably most useful for testing, this method may have real-world uses, so we are
        exposing it in the interface.

        :param ccode:
          (Usually) two-letter ISO country code.
        :param rates:
          10 element (MMI 1-10) array of loss rates which will be used to calculate losses.
        """
        self._overrides[ccode] = rates

    def getOverrideModel(self,ccode):
        """Get the override rates for the input country code.  If not set, None will be returned.

        :param ccode:
          ISO 2 letter country code.
        :returns:
          10 element (MMI 1-10) array of loss rates used to calculate losses for input country code,
          or None.
        """
        if ccode in self._overrides:
            return self._overrides[ccode]
        else:
            return None

    def clearOverrides(self):
        """Clear out any models that have been set manually using overrideModel().
        """
        self._overrides.clear()

    def getLossGrid(self,mmidata,popdata,isodata):
        """Calculate floating point losses on a grid.

        :param mmidata:
          Array of MMI values, dimensions (M,N).
        :param popdata:
          Array of population values, dimensions (M,N).
        :param isodata:
          Array of numeric country code values, dimensions (M,N).
        :returns:
          Grid of floating point loss values, dimensions (M,N).
        """
        ucodes = np.unique(isodata)
        fatgrid = np.zeros_like(mmidata)
        #we treat MMI 10 as MMI 9 for modeling purposes...
        mmidata[mmidata > 9.5] = 9.0
        
        for isocode in ucodes:
            countrydict = self._country.getCountry(int(isocode))
            if countrydict is None:
                ccode = 'unknown'
            else:
                ccode = countrydict['ISO2']
            
            if ccode not in self._overrides:
                rates = self.getLossRates(ccode,np.arange(5,10))
            else:
                rates = self.getOverrideModel(ccode)[4:9]

            tcidx = np.where(isodata == isocode)
            cidx = np.ravel_multi_index(tcidx,isodata.shape)
            for i in range(0,len(rates)):
                mmi = i+5
                mmi_lower = mmi-0.5
                mmi_upper = mmi+0.5
                midx = np.ravel_multi_index(np.where((mmidata >= mmi_lower) & (mmidata < mmi_upper)),mmidata.shape)
                idx = np.intersect1d(cidx,midx)
                idx2d = np.unravel_index(idx,mmidata.shape)
                fatgrid[idx2d] = popdata[idx2d]*rates[i]

        return fatgrid

    def getLossByShapes(self,mmidata,popdata,isodata,shapes,geodict,eventyear=None,gdpobj=None):
        """Divide the losses calculated per grid cell into polygons that intersect with the grid.

        :param mmidata:
          Array of MMI values, dimensions (M,N).
        :param popdata:
          Array of population values, dimensions (M,N).
        :param isodata:
          Array of numeric country code values, dimensions (M,N).
        :param shapes:
          Sequence of GeoJSON-like polygons as returned from fiona.open().
        :param eventyear:
          4 digit event year, must be not None if loss type is economic.
        :param gdpobj:
          GDP object, containing per capita GDP data from all countries.  
          Must not be None if calculating economic losses.
        :returns:
          Tuple of:
            1) modified sequence of polygons, including a new field "fatalities" or "dollars_lost".
            2) Total number of losses in all polygons.
        """
        lossgrid = self.getLossGrid(mmidata,popdata,isodata)
        polyshapes = []
        totloss = 0
        if self._loss_type == 'fatality':
            fieldname = 'fatalities'
        else:
            fieldname = 'dollars_lost'
        for polyrec in shapes:
            polygon = shapely.geometry.shape(polyrec['geometry'])
            #overlay the polygon on top of a grid, turn polygon pixels to 1, non-polygon pixels to 0.
            tgrid = Grid2D.rasterizeFromGeometry([polygon],geodict,fillValue=0,burnValue=1.0,attribute='value',mustContainCenter=True)
            #get the indices of the polygon cells
            shapeidx = tgrid.getData() == 1.0
            #get the sum of those cells in the loss grid
            losses = np.nansum(lossgrid[shapeidx])
            polyrec['properties'][fieldname] = int(losses)
            polyshapes.append(polyrec)
            totloss += int(losses)

        return (polyshapes,totloss)

    
            
            

#stdlib imports
from collections import OrderedDict
from datetime import datetime
import os.path
import json

#third party libraries
from lxml import etree
import numpy as np
from impactutils.time.timeutils import get_local_time,ElapsedTime
from mapio.city import Cities
import pandas as pd

#local imports
from losspager.utils.expocat import ExpoCat
from losspager.onepager.pagercity import PagerCities

DATETIMEFMT = '%Y-%m-%d %H:%M:%S'
TIMEFMT = '%H:%M:%S'
MINEXP = 1000 #minimum population required to declare maxmmi at a given intensity
SOFTWARE_VERSION = '2.0b' #THIS SHOULD GET REPLACED WITH SOMETHING SET BY VERSIONEER
EVENT_RADIUS = 400 #distance around epicenter to search for similar historical earthquakes

class PagerData(object):
    def __init__(self):
        self._pagerdict = OrderedDict()
        self._input_set = False
        self._exposure_set = False
        self._models_set = False
        self._comments_set = False
        self._mapinfo_set = True
        self._is_validated = False

    def __repr__(self):
        if not self._is_validated:
            return 'Unfilled PagerData object.'
        else:
            fmt = 'PagerData: ID %s Version %i Time %s Mag %.1f Fatality Alert %s Economic Alert %s'
            eid = self._pagerdict['event_info']['eventid']
            eversion = self._pagerdict['pager']['version_number']
            etime = self._pagerdict['event_info']['time']
            emag = self._pagerdict['event_info']['mag']
            fatalert = self._pagerdict['alerts']['fatality']['level']
            ecoalert = self._pagerdict['alerts']['economic']['level']
            return fmt % (eid,eversion,etime,emag,fatalert,ecoalert)
        
    #########Setters########
    def setInputs(self,shakegrid,pagerversion,eventcode):
        self._event_dict = shakegrid.getEventDict()
        self._shake_dict = shakegrid.getShakeDict()
        self._shakegrid = shakegrid
        self._pagerversion = pagerversion
        self._eventcode = eventcode
        self._input_set = True

    def setExposure(self,exposure,econ_exposure):
        nmmi,self._maxmmi = self._get_maxmmi(exposure)
        #convert all numpy integers to python integers
        new_exposure = {}
        for key,value in exposure.items():
            new_exposure[key] = value.tolist()
        new_econ_exposure = {}
        for key,value in econ_exposure.items():
            new_econ_exposure[key] = value.tolist()
        self._exposure = new_exposure
        self._econ_exposure = new_econ_exposure
        self._exposure_set = True

    def setComments(self,impact1,impact2,struct_comment,hist_comment,secondary_comment):
        """Set the comments.

        """
        self._impact1 = impact1
        self._impact2 = impact2
        self._struct_comment = struct_comment
        self._hist_comment = hist_comment
        self._secondary_comment = secondary_comment
        self._comments_set = True

    def setModelResults(self,fatmodel,ecomodel,
                        fatmodel_results,ecomodel_results,
                        semi_loss,res_fat,non_res_fat):
        self._fatmodel = fatmodel
        self._ecomodel = ecomodel
        self._fatmodel_results = fatmodel_results
        self._ecomodel_results = ecomodel_results
        self._semi_loss = semi_loss
        self._res_fat = res_fat
        self._non_res_fat = non_res_fat
        self._models_set = True

    def setMapInfo(self,cityfile,mapcities):
        self._city_file = cityfile
        self._map_cities = mapcities
        self._mapinfo_set = True

    def validate(self):
        if not self._input_set:
            raise PagerException('You must call setInputs() first.')
        if not self._exposure_set:
            raise PagerException('You must call setExposure() first.')
        if not self._models_set:
            raise PagerException('You must call setExposure() first.')
        if not self._comments_set:
            raise PagerException('You must call setComments() first.')
        if not self._mapinfo_set:
            raise PagerException('You must call setComments() first.')

        self._pagerdict['event_info'] = self._setEvent()
        self._pagerdict['pager'] = self._setPager()
        self._pagerdict['shake_info'] = self._setShakeInfo()
        self._pagerdict['alerts'] = self._setAlerts()
        self._pagerdict['population_exposure'] = self._setPopulationExposure()
        self._pagerdict['economic_exposure'] = self._setEconomicExposure()
        self._pagerdict['model_results'] = self._setModelResults()
        print('In pagerdata, getting city table.')
        self._pagerdict['city_table'] = self._getCityTable()
        print('In pagerdata, getting historical earthquakes.')
        self._pagerdict['historical_earthquakes'] = self._getHistoricalEarthquakes()
        print('In pagerdata, getting comments.')
        self._pagerdict['comments'] = self._getComments()
        self._is_validated = True
    #########Setters########

    #########Getters########
    def getEventInfo(self):
        """Return event summary information.

        :returns:
          Dictionary containing fields:
            - eventid Event ID.
            - time datetime object of origin.
            - lat Float latitude of origin.
            - lon Float longitude of origin.
            - depth Float depth of origin, km.
            - mag Float earthquake magnitude.
            - location String describing the location of the earthquake.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        event_info = self._pagerdict['event_info'].copy()
        event_info['time'] = datetime.strptime(event_info['time'],DATETIMEFMT)
        return self._pagerdict['event_info']

    def getImpactComments(self):
        """Return a tuple of the two impact comments.

        :returns:
          Tuple of impact comments, where first is most impactful, second is least.  In cases where the
          impact levels for fatalities and economic losses are the same, the second comment will be empty.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return(self._pagerdict['comments']['impact1'],self._pagerdict['comments']['impact2'])

    def getSoftwareVersion(self):
        """Return the Software version used to create this data structure.

        :returns:
          String describing PAGER software version.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['pager']['software_version']

    def getElapsed(self):
        """Return the string that summarizes the time elapsed between origin time and time of PAGER run.

        :returns:
          string summarizing time elapsed between origin time and time of PAGER run.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['pager']['elapsed_time']

    def getTotalExposure(self):
        """Return the array of aggregated (all countries) population exposure to shaking.

        :returns:
          List of aggregated (all countries) population exposure to shaking.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['population_exposure']['aggregated_exposure']

    def getHistoricalTable(self):
        """Return the list of representative historical earthquakes (if any).

        :returns:
          List of three dictionaries, containing fields:
            - EventID  14 character event ID based on time: (YYYYMMDDHHMMSS).
            - Time Pandas Timestamp object.
            - Lat  Event latitude.
            - Lon  Event longitude.
            - Depth  Event depth.
            - Magnitude  Event magnitude.
            - CountryCode  Two letter country code in which epicenter is located.
            - ShakingDeaths Number of fatalities due to shaking.
            - TotalDeaths Number of total fatalities.
            - Injured Number of injured.
            - Fire Integer (0 or 1) indicating if any fires occurred as a result of this earthquake.
            - Liquefaction Integer (0 or 1) indicating if any liquefaction occurred as a result of this earthquake.
            - Tsunami Integer (0 or 1) indicating if any tsunamis occurred as a result of this earthquake.
            - Landslide Integer (0 or 1) indicating if any landslides occurred as a result of this earthquake.
            - MMI1 - Number of people exposed to Mercalli intensity 1.
            - MMI2 - Number of people exposed to Mercalli intensity 2.
            - MMI3 - Number of people exposed to Mercalli intensity 3.
            - MMI4 - Number of people exposed to Mercalli intensity 4.
            - MMI5 - Number of people exposed to Mercalli intensity 5.
            - MMI6 - Number of people exposed to Mercalli intensity 6.
            - MMI7 - Number of people exposed to Mercalli intensity 7.
            - MMI8 - Number of people exposed to Mercalli intensity 8.
            - MMI9+ Number of people exposed to Mercalli intensity 9 and above.
            - MaxMMI  Highest intensity level with at least 1000 people exposed.
            - NumMaxMMI Number of people exposed at MaxMMI.
            - Distance Distance of this event from input event, in km.
            - Color The hex color that should be used for row color in historical events table.

        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['historical_earthquakes']

    def getStructureComment(self):
        """Return a paragraph describing the vulnerability of buildings in the most impacted country.

        :returns:
          Paragraph of text describing the vulnerability of buildings in the most impacted country.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['comments']['struct_comment']

    def getHistoricalComment(self):
        """Return a string describing the most impactful historical earthquake near the current event.

        :returns:
          string describing the most impactful historical earthquake near the current event.
        """
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['comments']['historical_comment']

    def getCityTable(self):
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['city_table']

    def getSummaryAlert(self):
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        return self._pagerdict['pager']['alert_level']
    #########Getters########

    #########Accessors########
    @property
    def time(self):
        return datetime.strptime(self._pagerdict['event_info']['time'],DATETIMEFMT)
    @property
    def magnitude(self):
        return self._pagerdict['event_info']['mag']
    @property
    def alert(self):
        if self._pagerdict['alerts']['fatality']['summary']:
            return self._pagerdict['alerts']['fatality']['level']
        else:
            return self._pagerdict['alerts']['economic']['level']
    @property
    def processing_time(self):
        return datetime.strptime(self._pagerdict['pager']['processing_time'],DATETIMEFMT)

    @property
    def version(self):
        return self._pagerdict['pager']['version_number']
    
    #########Accessors########
    
    #########Savers/Loaders########
    def saveToJSON(self,jsonfolder):
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')

        #one file to contain event summary, pager summary, and shakemap summary info
        event_info_file = os.path.join(jsonfolder,'event.json')
        f = open(event_info_file,'wt')
        infodict = {'event':self._pagerdict['event_info'],
                    'pager':self._pagerdict['pager'],
                    'shakemap':self._pagerdict['shake_info']}
        json.dump(infodict,f)
        f.close()

        #one file for alert information
        alert_info_file = os.path.join(jsonfolder,'alerts.json')
        f = open(alert_info_file,'wt')
        json.dump(self._pagerdict['alerts'],f)
        f.close()

        #one file for exposure information (population and economic)
        exposure_info_file = os.path.join(jsonfolder,'exposures.json')
        f = open(exposure_info_file,'wt')
        expdict = {'population_exposure':self._pagerdict['population_exposure'],
                   'economic_exposure':self._pagerdict['economic_exposure']}
        json.dump(expdict,f)
        f.close()

        #one file for loss model results
        loss_info_file = os.path.join(jsonfolder,'losses.json')
        f = open(loss_info_file,'wt')
        json.dump(self._pagerdict['model_results'],f)
        f.close()

        #one file for the table of affected cities
        city_file = os.path.join(jsonfolder,'cities.json')
        f = open(city_file,'wt')
        self._pagerdict['city_table'].to_json(f,orient='records')
        f.close()

        #one file for the table of historical earthquakes (if any)
        historical_info_file = os.path.join(jsonfolder,'historical_earthquakes.json')
        f = open(historical_info_file,'wt')
        json.dump(self._pagerdict['historical_earthquakes'],f)
        f.close()

        #one file for all comments
        comment_file = os.path.join(jsonfolder,'comments.json')
        f = open(comment_file,'wt')
        json.dump(self._pagerdict['comments'],f)
        f.close()
        
        
    def saveToLegacyXML(self):
        if not self._is_validated:
            raise PagerException('PagerData object has not yet been validated.')
        pass

    def loadFromJSON(self,jsonfolder):
        jsonfiles = ['event.json','alerts.json','exposures.json',
                     'losses.json','cities.json','historical_earthquakes.json',
                     'comments.json']
        missing = []
        for jf in jsonfiles:
            jsonfile = os.path.join(jsonfolder,jf)
            if not os.path.isfile(jsonfile):
                missing.append(jf)
        if len(missing):
            fmt = 'Could not load PagerData from %s: Missing required files %s'
            raise PagerException(fmt % jsonfolder,str(missing))

        #load event, shakemap, and pager basic information
        f = open(os.path.join(jsonfolder,'event.json'),'rt')
        event = json.load(f)
        f.close()
        self._pagerdict['event_info'] = event['event'].copy()
        self._pagerdict['pager'] = event['pager'].copy()
        self._pagerdict['shake_info'] = event['shakemap'].copy()

        #load the information about the alerts
        f = open(os.path.join(jsonfolder,'alerts.json'),'rt')
        self._pagerdict['alerts'] = json.load(f)
        f.close()

        #load the information about the exposures
        f = open(os.path.join(jsonfolder,'exposures.json'),'rt')
        expo = json.load(f)
        f.close()
        self._pagerdict['population_exposure'] = expo['population_exposure']
        self._pagerdict['economic_exposure'] = expo['economic_exposure']

        #load the information about the losses
        f = open(os.path.join(jsonfolder,'losses.json'),'rt')
        self._pagerdict['model_results'] = json.load(f)
        f.close()

        #load in the information about affected cities
        f = open(os.path.join(jsonfolder,'cities.json'),'rt')
        self._pagerdict['city_table'] = pd.read_json(f)
        f.close()

        #load in the information about historical earthquakes
        f = open(os.path.join(jsonfolder,'historical_earthquakes.json'),'rt')
        self._pagerdict['historical_earthquakes'] = json.load(f)
        f.close()

        #load in the information about comments
        f = open(os.path.join(jsonfolder,'comments.json'),'rt')
        self._pagerdict['comments'] = json.load(f)
        f.close()
        
        self._is_validated = True
        
    def loadFromLegacyXML(self):
        pass
    #########Savers/Loaders########
    
    def _get_maxmmi(self,exposure):
        maxmmi = 0
        for i in range(9,-1,-1):
            exp = exposure['TotalExposure'][i]
            if exp >= MINEXP:
                maxmmi = i + 1
                break
        return (maxmmi,exp)

    def _getComments(self):
        comment_dict = {}
        comment_dict['impact1'] = self._impact1
        comment_dict['impact2'] = self._impact2
        comment_dict['struct_comment'] = self._struct_comment
        comment_dict['historical_comment'] = self._hist_comment
        comment_dict['secondary_comment'] = self._secondary_comment
        return comment_dict
        
    def _setPager(self):
        pager = OrderedDict()
        process_time = datetime.utcnow()
        pager['software_version'] = SOFTWARE_VERSION
        pager['processing_time'] = process_time.strftime(DATETIMEFMT)
        pager['version_number'] = self._pagerversion
        pager['versioncode'] = self._event_dict['event_id']
        pager['eventcode'] = self._eventcode
        fatlevel = self._fatmodel.getAlertLevel(self._fatmodel_results)
        ecolevel = self._ecomodel.getAlertLevel(self._ecomodel_results)
        levels = {'green':0,'yellow':1,'orange':2,'red':3}
        rlevels = {0:'green',1:'yellow',2:'orange',3:'red'}
        pager['alert_level'] = rlevels[max(levels[fatlevel],levels[ecolevel])]
        maxmmi,nmmi = self._get_maxmmi(self._exposure)
        pager['maxmmi'] = maxmmi
        self._nmmi = nmmi
        etime = ElapsedTime()
        origin_time = self._event_dict['event_timestamp']
        etimestr = etime.getElapsedString(origin_time,process_time)
        pager['elapsed_time'] = etimestr
        #pager['tsunami'] = get_tsunami_info(self._eventcode,self._event_dict['magnitude'])
        #pager['ccode'] = get_epicenter_ccode(self._event_dict['lat'],self._event_dict['lon'])
        localtime = get_local_time(self._event_dict['event_timestamp'],
                                   self._event_dict['lat'],self._event_dict['lon'])
        ltimestr = localtime.strftime(DATETIMEFMT)
        pager['local_time_string'] = ltimestr

        return pager

    def _setEvent(self):
        event = OrderedDict()
        event['eventid'] = self._event_dict['event_id']
        event['time'] = self._event_dict['event_timestamp'].strftime(DATETIMEFMT)
        event['lat'] = self._event_dict['lat']
        event['lon'] = self._event_dict['lon']
        event['depth'] = self._event_dict['depth']
        event['mag'] = self._event_dict['magnitude']
        event['location'] = self._event_dict['event_description']
        return event

    def _setShakeInfo(self):
        shakeinfo = OrderedDict()
        shakeinfo['shake_version'] = self._shake_dict['shakemap_version']
        shakeinfo['shake_code_version'] = self._shake_dict['code_version']
        shakeinfo['shake_processing_time'] = self._shake_dict['process_timestamp'].strftime(DATETIMEFMT)

        return shakeinfo

    def _setAlerts(self):
        colors = {'0-1':'green',
                  '1-10':'yellow',
                  '10-100':'yellow',
                  '100-1000':'orange',
                  '1000-10000':'red',
                  '10000-100000':'red',
                  '100000-10000000':'red'}
        leveldict = {'green':0,
                     'yellow':1,
                     'orange':2,
                     'red':3}
        rleveldict = {0:'green',
                     1:'yellow',
                     2:'orange',
                     3:'red'}
        alerts = OrderedDict()

        
        fatlevel = self._fatmodel.getAlertLevel(self._fatmodel_results)
        ecolevel = self._ecomodel.getAlertLevel(self._ecomodel_results)
        is_fat_summary = rleveldict[leveldict[fatlevel]] > rleveldict[leveldict[ecolevel]]
        is_eco_summary = not is_fat_summary
        
        #Create the fatality alert level
        fat_gvalue = self._fatmodel.getCombinedG(self._fatmodel_results)
        fatality = OrderedDict([('type','fatality'),
                                ('units','fatalities'),
                                ('gvalue',fat_gvalue),
                                ('summary',is_fat_summary),
                                ('level',fatlevel),
                                ])
        bins = []
        fatprobs = self._fatmodel.getProbabilities(self._fatmodel_results,fat_gvalue)
        for prange,pvalue in fatprobs.items():
            color = colors[prange]
            rmin,rmax = prange.split('-')
            abin = OrderedDict([('color',color),
                                ('min',rmin),
                                ('max',rmax),
                                ('probability',pvalue)])
            bins.append(abin)
        fatality['bins'] = bins
        alerts['fatality'] = fatality

        #Create the economic alert level
        eco_gvalue = self._ecomodel.getCombinedG(self._ecomodel_results)
        economic = OrderedDict([('type','economic'),
                                ('units','USD'),
                                ('gvalue',eco_gvalue),
                                ('summary',is_eco_summary),
                                ('level',ecolevel),
                                ])
        bins = []
        ecoprobs = self._ecomodel.getProbabilities(self._ecomodel_results,eco_gvalue)
        for prange,pvalue in ecoprobs.items():
            color = colors[prange]
            rmin,rmax = prange.split('-')
            abin = OrderedDict([('color',color),
                                ('min',rmin),
                                ('max',rmax),
                                ('probability',pvalue)])
            bins.append(abin)
        economic['bins'] = bins
        alerts['economic'] = economic

        return alerts
        
    def _setPopulationExposure(self):
        exposure = OrderedDict()
        exposure['mmi'] = list(range(1,11))
        exposure['aggregated_exposure'] = list(self._exposure['TotalExposure'])
        country_exposures = []
        for ccode,exparray in self._exposure.items():
            if ccode == 'TotalExposure':
                continue
            expdict = OrderedDict()
            expdict['country_code'] = ccode
            expdict['exposure'] = list(exparray)
            country_exposures.append(expdict)
        exposure['country_exposures'] = country_exposures
        return exposure

    def _setEconomicExposure(self):
        exposure = OrderedDict()
        exposure['mmi'] = list(range(1,11))
        exposure['aggregated_exposure'] = list(self._econ_exposure['TotalEconomicExposure'])
        country_exposures = []
        for ccode,exparray in self._econ_exposure.items():
            if ccode == 'TotalEconomicExposure':
                continue
            expdict = OrderedDict()
            expdict['country_code'] = ccode
            expdict['exposure'] = list(exparray)
            country_exposures.append(expdict)
        exposure['country_exposures'] = country_exposures
        return exposure

    def _setModelResults(self):
        model_results = OrderedDict()

        #organize the empirical fatality model results
        empfat = OrderedDict()
        empfat['total_fatalities'] = self._fatmodel_results['TotalFatalities']
        country_deaths = []
        for ccode,deaths in self._fatmodel_results.items():
            if ccode == 'TotalFatalities':
                continue
            rates = list(self._fatmodel.getLossRates(ccode,np.arange(1,11)))
            fatdict = OrderedDict([('country_code',ccode),
                                   ('rates',rates),
                                   ('fatalities',deaths)])
            country_deaths.append(fatdict)
        empfat['country_fatalities'] = country_deaths
        model_results['empirical_fatality'] = empfat

        #organize the empirical economic model results
        empeco = OrderedDict()
        empeco['total_dollars'] = self._ecomodel_results['TotalDollars']
        country_dollars = []
        for ccode,dollars in self._ecomodel_results.items():
            if ccode == 'TotalDollars':
                continue
            rates = list(self._ecomodel.getLossRates(ccode,np.arange(1,11)))
            ecodict = OrderedDict([('country_code',ccode),
                                   ('rates',rates),
                                   ('us_dollars',dollars)])
            country_dollars.append(ecodict)
        empeco['country_dollars'] = country_dollars
        model_results['empirical_economic'] = empeco

        #organize the semi-empirical model results
        semimodel = OrderedDict()
        semimodel['fatalities'] = self._semi_loss
        semimodel['residental_fatalities'] = self._res_fat
        semimodel['non_residental_fatalities'] = self._non_res_fat
        model_results['semi_empirical_fatalities'] = semimodel

        return model_results

    def _getHistoricalEarthquakes(self):
        expocat = ExpoCat.fromDefault()
        clat,clon = self._event_dict['lat'],self._event_dict['lon']
        print('Select events by radius.')
        inbounds = expocat.selectByRadius(clat,clon,EVENT_RADIUS)
        maxmmi = self._pagerdict['pager']['maxmmi']
        nmmi = self._nmmi
        deaths = self._fatmodel_results['TotalFatalities']
        etime = self._event_dict['event_timestamp']
        print('Select historical earthquakes.')
        eventlist = inbounds.getHistoricalEvents(maxmmi,nmmi,deaths,clat,clon)
        for event in eventlist:
            if event is not None:
                event['Time'] = event['Time'].strftime(DATETIMEFMT)
        return eventlist

    def _getCityTable(self):
        cities = Cities.loadFromGeoNames(self._city_file)
        pcities = PagerCities(cities,self._shakegrid.getLayer('mmi'))
        city_table = pcities.getCityTable(self._map_cities)
        return city_table

from collections import OrderedDict
from lxml import etree
from datetime import datetime
from impactutils.time.timeutils import get_local_time,ElapsedTime
from losspager.utils.expocat import ExpoCat

DATETIMEFMT = '%Y-%m-%d %H:%M:%S'
TIMEFMT = '%H:%M:%S'
MINEXP = 1000 #minimum population required to declare maxmmi at a given intensity
SOFTWARE_VERSION = '2.0b' #THIS SHOULD GET REPLACED WITH SOMETHING SET BY VERSIONEER

class PagerData(object):
    def __init__(self):
        self._pagerdict = OrderedDict()
        self._input_set = False
        self._exposure_set = False
        self._models_set = False

    def setInputs(self,shakegrid,pagerversion,eventcode):
        self._event_dict = shakegrid.getEventDict()
        self._shake_dict = shakegrid.getShakeDict()
        self._pagerversion = pagerversion
        self._eventcode = eventcode
        self._input_set = True
        

    def setExposure(self,exposure,econ_exposure):
        nmmi,self._maxmmi = self._get_maxmmi(exposure)
        self._exposure = exposure
        self._econ_exposure = econ_exposure
        self._exposure_set = True

    def _get_maxmmi(self,exposure):
        for i in range(9,-1,-1):
            exp = exposure['TotalExposure'][i]
            if exp >= MINEXP:
                maxmmi = i + 1
                break
        return (maxmmi,exp)

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
        pass

    def validate(self):
        if not self._input_set:
            raise PagerException('You must call setInputs() first.')
        if not self._exposure_set:
            raise PagerException('You must call setExposure() first.')
        if not self._models_set:
            raise PagerException('You must call setExposure() first.')

        self._pagerdict['event'] = self._setEvent()
        self._pagerdict['pager'] = self._setPager()
        self._pagerdict['shakeinfo'] = self._setShakeInfo()
        self._pagerdict['alerts'] = self._setAlerts()
        self._pagerdict['population_exposure'] = self._setPopulationExposure()
        self._pagerdict['economic_exposure'] = self._setEconomicExposure()
        self._pagerdict['model_results'] = self._setModelResults()
        self._pagerdict['historical_earthquakes'] = self._getHistoricalEarthquakes()
        

        
        
    def _setPager(self):
        pager = OrderedDict()
        process_time = datetime.utcnow().strftime(DATETIMEFMT)
        pager['software_version'] = SOFTWARE_VERSION
        pager['processing_time'] = process_time
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
        origin_time = self._edict['event_timestamp']
        etimestr = etime.getElapsedString(origin_time,process_time)
        pager['elapsed_time'] = etimestr
        #pager['tsunami'] = get_tsunami_info(self._eventcode,self._event_dict['magnitude'])
        #pager['ccode'] = get_epicenter_ccode(self._event_dict['lat'],self._event_dict['lon'])
        localtime = get_local_time(edict['event_timestamp'],edict['lat'],edict['lon'])
        ltimestr = localtime.strftime(DATETIMEFMT)
        pager['local_time_string'] = ltimestr

        return pager

    def _setEvent(self):
        event = OrderedDict()
        event['time'] = self._edict['event_timestamp']
        event['lat'] = self._edict['lat']
        event['lon'] = self._edict['lon']
        event['depth'] = self._edict['depth']
        event['magnitude'] = self._edict['magnitude']

        return event

    def _setShakeInfo(self):
        shakeinfo = OrderedDict()
        shakeinfo['shake_version'] = self._sdict['shakemap_version']
        shakeinfo['shake_code_version'] = self._sdict['code_version']
        shakeinfo['shake_time'] = self._sdict['process_timestamp']

        return shakeinfo

    def _setAlerts(self):
        colors = {'0-1':'green',
                  '1-10':'yellow',
                  '10-100':'yellow',
                  '100-1000':'orange',
                  '1000-10000':'red',
                  '10000-100000':'red',
                  '100000-1000000':'red'}
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
        fatality = OrderedDict([('type','fatality')
                                ('units','fatalities'),
                                ('gvalue',fat_gvalue),
                                ('summary',is_fat_summary),
                                ('level',fatlevel),
                                ])
        bins = []
        fatprobs = self._fatmodel.getProbabilities(self._fatmodel_results,gvalue)
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
        economic = OrderedDict([('type','economic')
                                ('units','USD'),
                                ('gvalue',eco_gvalue),
                                ('summary',is_eco_summary),
                                ('level',ecolevel),
                                ])
        bins = []
        ecoprobs = self._ecomodel.getProbabilities(self._ecomodel_results,gvalue)
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
        for ccode,exposure in self._exposure.items():
            if ccode == 'TotalExposure':
                continue
            expdict = OrderedDict()
            expdict['country_code'] = ccode
            expdict['exposure'] = list(exposure)
            country_exposures.append(expdict)
        exposure['country_exposures'] = country_exposures
        return exposure

    def _setEconomicExposure(self):
        exposure = OrderedDict()
        exposure['mmi'] = list(range(1,11))
        exposure['aggregated_exposure'] = list(self._econ_exposure['TotalEconomicExposure'])
        country_exposures = []
        for ccode,exposure in self._econ_exposure.items():
            if ccode == 'TotalEconomicExposure':
                continue
            expdict = OrderedDict()
            expdict['country_code'] = ccode
            expdict['exposure'] = list(exposure)
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
        semimodel['residental_fatalities'] = self._resfat
        semimodel['non_residental_fatalities'] = self._resfat
        model_results['semi_empirical_fatalities'] = semimodel

        return model_results

    def _getHistoricalEarthquakes(self):
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this file?
        expocat = ExpoCat.fromDefault()
        clat,clon = self._edict['lat'],self._edict['lon']
        inbounds = expocat.selectByRadius(clat,clon,EVENT_RADIUS)
        maxmmi = self._pagerdict['pager']['maxmmi']
        nmmi = self._nmmi
        deaths = self._fatmodel_results['TotalFatalities']
        etime = self._edict['event_timestamp']
        eventlist = inbounds.getHistoricalEvents(maxmmi,nmmi,clat,clon)
        return eventlist
            
        
        
        
        
#     #TODO - think about whether this class should also be instantiable from JSON
#     #that it creates.  Talk to Eric and Bruce (web team?) about how to organize the data in it.
#     #if we make a json loader from a file as a class method, how ugly is the constructor going to be?
#     def __init__(self,shakegrid,pagerversion,exposure,econexp,fatmodel,fatdict,
#                  ecomodel,ecodict,semiloss,semires,seminonres,cities,impact1,impact2,
#                  structcomment,histeq,secondarycomment):
#         """Assemble PAGER model results into a data structure that can be rendered in multiple formats.

        

#         :param shakegrid:
#           ShakeGrid object.
#         :param pagerversion:
#           Integer indicating the PAGER version.
#         :param exposure:
#           PAGER Exposure object dictionary.
#         :param econexp:
#           PAGER EconExposure object dictionary.
#         :param fatmodel:
#           PAGER LossModel object, containing fatality information.
#         :param fatdict:
#           PAGER fatality results dictionary.
#         :param ecomodel:
#           PAGER LossModel object, containing dollar loss information.
#         :param ecodict:
#           PAGER economic results dictionary.
#         :param semiloss:
#           PAGER semi-empirical loss model results value (integer number of fatalities).
#         :param semires:
#           PAGER semi-empirical loss model results by residential buildings, per country.
#         :param seminonres:
#           PAGER semi-empirical loss model results by non-residential buildings, per country.
#         :param cities:
#           An instance of the MapIO Cities object.
#         :param impact1:
#           String containing first impact comment.
#         :param impact2:
#           String containing second impact comment.
#         :param structcomment:
#           String comment describing vulnerability of structures in the region.
#         :param histeq:
#           List of historical earthquake dictionaries deemed to be similar to 
#           the current event (described in shakegrid).
#           Attributes?
#         :param secondarycomment:
#           String comment describing secondary hazards in the area.
#         :returns:
#           PAGERData object, which can be rendered as JSON or XML.
#           Details?
#         """
#         #Internally, this thing will be a big dictionary, making it really easy to render as JSON,
#         #and easy-ish to render as XML using lxml.
        
#         self._pager_dict = OrderedDict()
#         self._pager_dict['pager'] = {'software_version':SOFTWARE_VERSION}
#         #impact has:
#         # aggregated exposures
#         # exposures
#         # aggregated economic exposures
#         # economic exposures
#         # empirical fatality model results (median and median per country)
#         # empirical economic model results (median and median per country)
#         # semi-empirical, maybe this stuff:
#         # <results_by_country ccode="EC">
# 		# 		<buildings>
# 		# 			<building pagertype="W2" collapses="0.463680619841" deaths="0.0038960854833"/>
# 		# 			<building pagertype="M" collapses="1.61855163028" deaths="0.0627688234684"/>
# 		# 			<building pagertype="UFB" collapses="37.3896126762" deaths="1.93333509105"/>
# 		# 		</buildings>
# 		# 	</results_by_country>
# 		# 	<population_by_structure A="29.5873394756" UFB="1618.09476028" M="14.0090775204" W2="40.1330277425" W="42.2701241386" INF="3.3270903828"/>
#         self._pager_dict['pager']['impact'] = self._get_impact(exposure,econexp,
#                                                                fatdict,ecodict,
#                                                                semiloss,semires,seminonres)
#         #event is just the one element
#         self._pager_dict['pager']['event'] = self._get_event(shakegrid,pagerversion,maxmmi)
#         #alerts have the loss probability information
#         self._pager_dict['pager']['fatality_alert'] = self._get_alert(fatmodel,fatdict,'fatality')
#         self._pager_dict['pager']['economic_alert'] = self._get_alert(ecomodel,ecodict,'economic')
#         #empirical_loss_rates:
#         #  fatalities
#         #    ccode1 - mmi, rates
#         #    ccode2 - mmi, rates
#         #  economic
#         #    ccode1 - mmi, rates
#         #    ccode2 - mmi, rates
#         self._pager_dict['pager']['empirical_loss_rates'] = self._get_loss_rates(fatmodel,ecomodel,fatdict,ecodict)
#         #historical events:
#         # <historical_events>
# 		# <historical_event distance="200.727179547" color="#ffff00" magnitude="5.7" maxmmi="6" shakingdeaths="0" date="2005-01-30 07:06:49" maxmmiexp="168068"/>
# 		# <historical_event distance="276.915490212" color="#ffff00" magnitude="5.5" maxmmi="6" shakingdeaths="1" date="2000-09-20 08:37:18" maxmmiexp="99064"/>
# 		# <historical_event distance="223.234677742" color="#ff0000" magnitude="7.1" maxmmi="9" shakingdeaths="1000" date="1987-03-06 04:10:44" maxmmiexp="2341"/>
#         self._pager_dict['pager']['hist_eq'] = self._get_hist_eq(histeq)
#         #     <comments>
#         # 	<structure_comment>
#         # 		Overall, the population in this region resides in structures that are vulnerable to earthquake shaking, though some resistant structures exist.  The predominant vulnerable building types are unreinforced brick masonry and mud wall construction.
#         # 	</structure_comment>
#         # 	<impact1 type="fatality">
#         # 		Green alert for shaking-related fatalities and economic losses.  There is a low likelihood of casualties and damage.
#         # 	</impact1>
#         # 	<impact2 type="economic">
#         # 	</impact2>
#         # 	<secondary_comment>
#         # 		Recent earthquakes in this area have caused secondary hazards such as landslides that might have contributed to losses.
#         # 	</secondary_comment>
#         # </comments>
#         self._pager_dict['pager']['comments'] = self._get_comments(impact1,impact2,structcomment,secondary_comment)
#         self._pager_dict['pager']['cities'] = self._get_comments(cities)

#     def _get_maxmmi(self,exposure):
#         for i in range(9,-1,-1):
#             exp = exposure['TotalExposure'][i]
#             if exp >= MINEXP:
#                 maxmmi = i + 1
#                 break
#         return (maxmmi,exp)
        
#     def _get_impact(self,exposure,econexp,fatdict,ecodict,semiloss,resfat,nonresfat):
#         impact = OrderedDict()
#         impact['aggregated_exposures'] = exposure['TotalExposure']
#         impact['exposures_by_country'] = OrderedDict()
#         for ccode,expolist in exposure.items():
#             if ccode == 'TotalExposure':
#                 continue
#             impact['exposures_by_country'][ccode] = expolist

#         #do economic exposure
#         impact['aggregated_economic_exposures'] = econexp['TotalEconomicExposure']
#         impact['economic_exposures_by_country'] = OrderedDict()
#         for ccode,expolist in econexp.items():
#             if ccode == 'TotalEconomicExposure':
#                 continue
#             impact['economic_exposures_by_country'][ccode] = expolist

#         #do empirical fatality model
#         empfat = OrderedDict()
#         empfat['median_total_losses'] = fatdict['TotalFatalities']
#         for ccode,value in fatdict.items():
#             if ccode == 'TotalFatalities':
#                 continue
#             empfat['%s_losses' % ccode] = value

#         impact['empirical_fatality_model'] = empfat
            
#         #do empirical economic model
#         empeco = OrderedDict()
#         empeco['median_total_losses'] = ecodict['TotalDollars']
#         for ccode,value in ecodict.items():
#             if ccode == 'TotalDollars':
#                 continue
#             empeco['%s_losses' % ccode] = value

#         impact['empirical_economic_model'] = empeco

#         #do semi-empirical fatality model
#         semi = OrderedDict()
#         semi['median_total_losses'] = semiloss
#         semi['residential_fatalities'] = resfat
#         semi['non_residential_fatalities'] = nonresfat
#         return impact

#     def _get_event(self,shakegrid,pagerversion,maxmmi):
#         edict = shakegrid.getEventDict()
#         sdict = shakegrid.getShakeDict()
#         etime = edict['event_timestamp'].strftime(DATETIMEFMT)
#         shaketime = sdict['process_timestamp'].strftime(DATETIMEFMT)
#         localtime = get_local_time(edict['event_timestamp'],edict['lat'],edict['lon'])
#         ltimestr = localtime.strftime(DATETIMEFMT)
#         event = OrderedDict()
#         event['eventcode'] = sdict['event_id']
#         event['versioncode'] = sdict['event_id']
#         event['number'] = '{:d}'.format(pagerversion)
#         event['shakeversion'] = '{:d}'.format(sdict['shakemap_version'])
#         event['magnitude'] = '{:.1f}'.format(edict['magnitude'])
#         event['depth'] = '{:.1f}'.format(edict['depth'])
#         event['lat'] = '{:.4f}'.format(edict['lat'])
#         event['lon'] = '{:.4f}'.format(edict['lon'])
#         event['event_timestamp'] = etime
#         event['event_description'] = edict['event_description']
#         event['maxmmi'] = '{:.1f}'.format(maxmmi)
#         event['shaketime'] = shaketime
#         event['localtime'] = ltimestr

#         return event
        
#     def renderToJSON(self,jsonfile):
#         f = open(jsonfile,'wt')
#         json.dump(self._pager_dict,f,indent=2)
#         f.close()
    



# def add_alert(parent,lossmodel,lossdict,losstype,alertlevel,summary=False):
#     #     <alert type="economic" level="red" summary="yes" units="USD">
#     # <bin min="0" max="999999" probability="0" color="green"/>
#     # <bin min="1000000" max="9999999" probability="1" color="yellow"/>
#     # <bin min="10000000" max="99999999" probability="8" color="yellow"/>
#     # <bin min="100000000" max="999999999" probability="26" color="orange"/>
#     # <bin min="1000000000" max="9999999999" probability="35" color="red"/>
#     # <bin min="10000000000" max="99999999999" probability="22" color="red"/>
#     # <bin min="100000000000" max="999999999999" probability="6" color="red"/>
#     # </alert>
#     yesdict = {True:'yes',False:'no'}
    
#     #what is the alert level?
#     gvalue = lossmodel.getCombinedG(lossdict)
#     if losstype == 'fatality':
#         leveldict = {'0':'green',
#                      '9':'yellow',
#                      '99':'yellow',
#                      '999':'orange',
#                      '999999':'red',
#                      '9999999':'red',
#                      '99999999':'red',
#                      '999999999':'red',}
#         key = 'TotalFatalities'
#         units = 'fatalities'
#     else:
#         leveldict = {'999999':'green',
#                      '9999999':'yellow',
#                      '99999999':'yellow',
#                      '999999999':'orange',
#                      '9999999999':'red',
#                      '99999999999':'red',
#                      '999999999999':'red',
#                      '10000000000000000':'red'}
#         key = 'TotalDollars'
#         units = 'USD'
#     expected = lossdict[key]
#     alert = etree.SubElement(parent,'alert',type=losstype,summary=yesdict[summary],units=units)
#     probs = lossmodel.getProbabilities(lossdict,gvalue)
#     for probrange,value in probs.items():
#         pmin,pmax = probrange.split('-')
#         pvaluestr = '{:.1f}'.format(value*100)
#         pmax = '{:d}'.format(int(pmax)-1)
#         for lvalue,color in leveldict.items():
#             if pmax == lvalue:
#                 pcolor = color
#         bintag = etree.SubElement(alert,'bin',min=pmin,max=pmax,probability=pvaluestr,color=pcolor)
#     return alert

# def get_pagerdoc(shakegrid,pagerversion,exposure,econexp,fatmodel,fatdict,
#                  ecomodel,ecodict,cities,impact1,impact2,
#                  structcomment,histeq,secondarycomment):
#     """Assemble PAGER model data and metadata into an lxml ElementTree object.

#     This XML file will be the legacy PAGER XML.  The expanded content will either
#     be in another XML file or a JSON file.

#     :param shakegrid:
#       ShakeGrid object.
#     :param pagerversion:
#       Integer indicating the PAGER version.
#     :param exposure:
#       PAGER Exposure object dictionary.
#     :param econexp:
#       PAGER EconExposure object dictionary.
#     :param fatmodel:
#       PAGER LossModel object, containing fatality information.
#     :param fatdict:
#       PAGER fatality results dictionary.
#     :param ecomodel:
#       PAGER LossModel object, containing dollar loss information.
#     :param ecodict:
#       PAGER economic results dictionary.
#     :param cities:
#       An instance of the MapIO Cities object.
#     :param impact1:
#       String containing first impact comment.
#     :param impact2:
#       String containing second impact comment.
#     :param structcomment:
#       String comment describing vulnerability of structures in the region.
#     :param histeq:
#       List of historical earthquake dictionaries deemed to be similar to 
#       the current event (described in shakegrid).
#       Attributes?
#     :param secondarycomment:
#       String comment describing secondary hazards in the area.
#     :returns:
#       lxml ElementTree object, containing the PAGER results in XML form.
#       Details?
#     """
#     leveldict = {'green':0,
#                  'yellow':1,
#                  'orange':2,
#                  'red':3}
#     pager = etree.Element('pager')
#     doc = etree.ElementTree(pager)
#     exp = exposure['TotalExposure']
#     for i in range(9,-1,-1):
#         exp = exposure['TotalExposure'][i]
#         if exp >= MINEXP:
#             maxmmi = i
#             break
        
#     event = get_event(pager,shakegrid,pagerversion,maxmmi)
#     alerts = etree.SubElement(event,'alerts')
#     fatalertlevel = fatmodel.getAlertLevel(fatdict)
#     ecoalertlevel = ecomodel.getAlertLevel(ecodict)
#     isfathigher = leveldict[fatalertlevel] >= leveldict[ecoalertlevel]
#     isecohigher = leveldict[ecoalertlevel] > leveldict[fatalertlevel]
#     fatalert = add_alert(alerts,fatmodel,'fatality',summary=isfathigher)
#     ecoalert = add_alert(alerts,fatmodel,'fatality',fatalertlevel,summary=isecohigher)
#     impact = etree.SubElement(pager,'impact')
#     exposure = add_exposure(impact,expdict)
    

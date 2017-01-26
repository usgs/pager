#stdlib imports
import re

#third party imports
from scipy.special import erf
import numpy as np
import pandas as pd
from impactutils.textformat.text import set_num_precision,commify,round_to_nearest
from openquake.hazardlib.geo.geodetic import geodetic_distance

#local imports
from losspager.models.emploss import EmpiricalLoss
from losspager.models.econexposure import GDP
from losspager.utils.country import Country
from losspager.utils.compass import get_compass_dir
from losspager.utils.expocat import ExpoCat
from losspager.utils.mathutil import invphi
from losspager.utils.region import PagerRegions

GREEN_FAT_HIGH = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
YELLOW_FAT_HIGH = '''Yellow alert for shaking-related fatalities. Some casualties are possible and the impact should be relatively localized.
Past events with this alert level have required a local or regional level response.'''
ORANGE_FAT_HIGH = '''Orange alert for shaking-related fatalities. Significant casualties are likely and the disaster is potentially widespread.
Past events with this alert level have required a regional or national level response.'''
RED_FAT_HIGH = '''Red alert for shaking-related fatalities. High casualties are probable and the disaster is likely widespread.
Past events with this alert level have required a national or international level response.'''

GREEN_ECON_HIGH = 'Green alert for economic losses. There is a low likelihood of damage.'
YELLOW_ECON_HIGH = '''Yellow alert for economic losses. Some damage is possible and the impact should be relatively localized. [GDPCOMMENT]
Past events with this alert level have required a local or regional level response.'''
ORANGE_ECON_HIGH = '''Orange alert for economic losses. Significant damage is likely and the disaster is potentially widespread. [GDPCOMMENT]
Past events with this alert level have required a regional or national level response.'''
RED_ECON_HIGH = '''Red alert for economic losses. Extensive damage is probable and the disaster is likely widespread. [GDPCOMMENT]
 Past events with this alert level have required a national or international level response.'''

GREEN_FAT_LOW = 'Green alert for shaking-related fatalities. There is a low likelihood of casualties.'
YELLOW_FAT_LOW = 'Yellow alert for shaking-related fatalities. Some casualties are possible.'
ORANGE_FAT_LOW = 'Orange alert for shaking-related fatalities. Significant casualties are likely.'
RED_FAT_LOW = ''


GREEN_ECON_LOW = 'Green alert for economic losses. There is a low likelihood of damage.'
YELLOW_ECON_LOW = 'Yellow alert for economic losses. Some damage is possible. [GDPCOMMENT]'
ORANGE_ECON_LOW = 'Orange alert for economic losses. Significant damage is likely. [GDPCOMMENT]'
RED_ECON_LOW = ''

GREEN_FAT_EQUAL = '''Green alert for shaking-related fatalities and economic losses.
There is a low likelihood of casualties and damage.'''
YELLOW_FAT_EQUAL = '''Yellow alert for shaking-related fatalities and economic losses.
Some casualties and damage are possible and the impact should be relatively localized.
Past yellow alerts have required a local or regional level response.'''
ORANGE_FAT_EQUAL = '''Orange alert for shaking-related fatalities and economic losses.
Significant casualties and damage are likely and the disaster is potentially widespread.
Past orange alerts have required a regional or national level response.'''
RED_FAT_EQUAL = '''Red alert for shaking-related fatalities and economic losses.
High casualties and extensive damage are probable and the disaster is likely widespread.
Past red alerts have required a national or international response.'''

GREEN_ECON_EQUAL = ''
YELLOW_ECON_EQUAL = '[GDPCOMMENT]'
ORANGE_ECON_EQUAL = '[GDPCOMMENT]'
RED_ECON_EQUAL = '[GDPCOMMENT]'

EPS = 1e-12 #if expected value is zero, take the log of this instead
SEARCH_RADIUS = 400 #kilometer radius to search for historical earthquakes

def get_gdp_comment(ecodict,ecomodel,econexposure,event_year):
    """Create a comment on the GDP impact of a given event in the most impacted country.

    :param ecodict:
      Dictionary containing country code keys and integer population estimations of economic loss.
    :param ecomodel:
      Instance of the EmpiricalLoss class.
    :param econexposure:
      Dictionary containing country code (ISO2) keys, and values of
      10 element arrays representing population exposure to MMI 1-10.
      Dictionary will contain an additional key 'Total', with value of exposure across all countries.
    :param event_year:
      Year in which event occurred.
    :returns:
      A string which indicates what fraction of the country's GDP the losses represent.
    """
    #get the gdp comment
    #get the G value for the economic losses
    eco_gvalue = ecomodel.getCombinedG(ecodict)
    #get the country code of the country with the highest losses
    dccode = ''
    dmax = 0
    expected = ecodict['TotalDollars']/1e6
    if ecodict['TotalDollars'] > 0:    
        for ccode,value in ecodict.items():
            if ccode == 'TotalDollars':
                continue
            if value > dmax:
                dmax = value
                dccode = ccode
    else:
        #how do I compare economic exposure between countries?
        #do I want to compare that, or just grab the country of epicenter?
        for ccode,value in ecodict.items():
            rates = ecomodel.getLossRates(ccode,np.arange(1,10))
            emploss = np.nansum(rates * value)
            if emploss > dmax:
                dmax = emploss
                dccode = ccode
    gdp_obj = GDP.fromDefault()
    gdp,outccode = gdp_obj.getGDP(dccode,event_year)
    country = Country()
    cinfo = country.getCountry(outccode)
    if cinfo is not None:
        pop = cinfo['Population']
    else:
        pop = 0
    T = (pop * gdp)/1e6
    if T == 0:
        return ''
    percent = erf(1/np.sqrt(2))
    plow = round(np.exp(np.log(max(expected,EPS))-eco_gvalue * invphi(percent)))
    phigh =round(np.exp(eco_gvalue * invphi(percent) + np.log(max(expected,EPS))))
    if plow != 0:
        ptlow = int(plow*1e2/T)
    else:
        ptlow = 0
    if phigh != 0:
        pthigh = int(phigh*1e2/T)
    else:
        pthigh = 0
    if dccode in ['XF','EU','WU']:
        cname = 'the United States'
    else:
        cname = cinfo['Name']
    if pthigh < 1.0:
        strtxt = 'Estimated economic losses are less than 1%% of GDP of %s.' % cname
    else:
        if ptlow < 100:
            ptlow = set_num_precision(ptlow,1)
        else:
            ptlow = set_num_precision(ptlow,2)
        if pthigh < 100:
            pthigh = set_num_precision(pthigh,1)
        else:
            pthigh = set_num_precision(pthigh,2)
        if pthigh >= 100:
            strtxt = 'Estimated economic losses may exceed the GDP of %s.' % cname
        else:
            strtxt = 'Estimated economic losses are %i-%i%% GDP of %s.' % (ptlow,pthigh,cname)
    return strtxt
    

def get_impact_comments(fatdict,ecodict,econexposure,event_year):
    """Create comments for a given event, describing economic and human (fatality) impacts.

    :param fatdict:
      Dictionary containing country code keys and integer population estimations of human loss.
    :param ecodict:
      Dictionary containing country code keys and integer population estimations of economic loss.
    :param econexposure:
      Dictionary containing country code (ISO2) keys, and values of
      10 element arrays representing population exposure to MMI 1-10.
      Dictionary will contain an additional key 'Total', with value of exposure across all countries.
    :param event_year:
      Year in which event occurred.
    :returns:
      A tuple of two strings which describe the economic and human impacts.  The most impactful
      of these will be the first string.  Under certain situations, the second comment could be blank.
    """
    #first, figure out what the alert levels are for each loss result
    
    fatmodel = EmpiricalLoss.fromDefaultFatality()
    ecomodel = EmpiricalLoss.fromDefaultEconomic()
    fatlevel = fatmodel.getAlertLevel(fatdict)
    ecolevel = fatmodel.getAlertLevel(ecodict)
    levels = {'green':0,'yellow':1,'orange':2,'red':3}
    rlevels = {0:'green',1:'yellow',2:'orange',3:'red'}
    fat_higher = levels[fatlevel] > levels[ecolevel]
    eco_higher = levels[ecolevel] > levels[fatlevel]
    gdpcomment = get_gdp_comment(ecodict,ecomodel,econexposure,event_year)

    if fat_higher:
        if fatlevel == 'green':
            impact1 = GREEN_FAT_HIGH
        elif fatlevel == 'yellow':
            impact1 = YELLOW_FAT_HIGH
        elif fatlevel == 'orange':
            impact1 = ORANGE_FAT_HIGH
        elif fatlevel == 'red':
            impact1 = RED_FAT_HIGH

        if ecolevel == 'green':
            impact2 = GREEN_ECON_LOW
        elif ecolevel == 'yellow':
            impact2 = YELLOW_ECON_LOW
        elif ecolevel == 'orange':
            impact2 = ORANGE_ECON_LOW
        elif ecolevel == 'red':
            impact2 = RED_ECON_LOW
        impact2 = impact2.replace('[GDPCOMMENT]',gdpcomment)
    elif eco_higher:
        if ecolevel == 'green':
            impact1 = GREEN_ECON_HIGH
        elif ecolevel == 'yellow':
            impact1 = YELLOW_ECON_HIGH
        elif ecolevel == 'orange':
            impact1 = ORANGE_ECON_HIGH
        elif ecolevel == 'red':
            impact1 = RED_ECON_HIGH

        if fatlevel == 'green':
            impact2 = GREEN_FAT_LOW
        elif fatlevel == 'yellow':
            impact2 = YELLOW_FAT_LOW
        elif fatlevel == 'orange':
            impact2 = ORANGE_FAT_LOW
        elif fatlevel == 'red':
            impact2 = RED_FAT_LOW
        impact1 = impact1.replace('[GDPCOMMENT]',gdpcomment)
    else:
        if fatlevel == 'green':
            impact1 = GREEN_FAT_EQUAL
        elif fatlevel == 'yellow':
            impact1 = YELLOW_FAT_EQUAL
        elif fatlevel == 'orange':
            impact1 = ORANGE_FAT_EQUAL
        elif fatlevel == 'red':
            impact1 = RED_FAT_EQUAL

        if ecolevel == 'green':
            impact2 = GREEN_ECON_EQUAL
        elif ecolevel == 'yellow':
            impact2 = YELLOW_ECON_EQUAL
        elif ecolevel == 'orange':
            impact2 = ORANGE_ECON_EQUAL
        elif ecolevel == 'red':
            impact2 = RED_ECON_EQUAL
        impact2 = impact2.replace('[GDPCOMMENT]',gdpcomment)

    impact1 = impact1.replace('\n',' ')
    impact2 = impact2.replace('\n',' ')
    return (impact1,impact2)

def _add_dicts(d1,d2):
    """Add two dictionaries of losses per building type together.  Dictionaries must contain identical keys.

    :param d1:
      Dictionary of losses by building type.
    :param d2:
      Dictionary of losses by building type.
    :returns:
      Pandas Series object with summed losses per building type.
    """
    #operating under assumption that both d1 and d2 have the same keys
    df1 = pd.DataFrame(d1,index=['fats'])
    df2 = pd.DataFrame(d2,index=['fats'])
    df3 = df1 + df2
    df4 = df3.sort_values('fats',axis=1,ascending=False)
    return df4.loc['fats']

def get_structure_comment(resfat,nonresfat,semimodel):
    """Create a paragraph describing the vulnerability of buildings in the most impacted country.

    :param resfat:
      Dictionary of losses by building type in residential areas.
    :param nonresfat:
      Dictionary of losses by building type in non-residential areas.
    :param semimodel:
      Instance of SemiEmpiricalFatality class.
    :returns:
      Paragraph of text describing the vulnerability of buildings in the most impacted country.
    """
    maxccode = ''
    maxfat = 0
    ccodes = resfat.keys()
    if not len(ccodes):
        return 'There are likely to be no affected structures in this region.'
    for ccode in ccodes:
        resfatdict = resfat[ccode]
        nonresfatdict = nonresfat[ccode]
        resfatsum = np.array(list(resfatdict.values())).sum()
        nonresfatsum = np.array(list(resfatdict.values())).sum()
        fatsum = resfatsum + nonresfatsum
        if fatsum >= maxfat:
            maxfat = fatsum
            maxccode = ccode

    #get a pandas Series of all the unique building types in the 
    #country of greatest impact, sorted by losses (high to low).
    stypes = _add_dicts(resfat[maxccode],nonresfat[maxccode])
        
    pregions = PagerRegions()
    regioncode = pregions.getRegion(maxccode)
    default = pregions.getComment(regioncode)
    if len(stypes) == 0:
        if default != '':
            return default
        else:
            return 'There are likely to be no affected structures in this region.'

    tstarts = ['W*','S*','C*','P*','RM*','MH','M*','A*','RE','RS*','DS*','UFB*','UCB','MS','TU','INF','UNK']
    categories = []
    btypes = []
    for stype in stypes.index:
        if stype in tstarts:
            btypes.append(stype)
            categories.append(stype)
        else:
            nc = 1
            while nc <= len(stype):
                ns = stype[0:nc] + '*'
                if ns in tstarts and ns not in categories:
                    btypes.append(stype)
                    categories.append(ns)
                    break
                nc += 1
        if len(btypes) == 2:
            break

    fmt1 = 'The predominant vulnerable building type is %s construction.'
    fmt2 = 'The predominant vulnerable building types are %s and %s construction.'
    if len(btypes) == 2:
        b1 = semimodel.getBuildingDesc(btypes[0])
        b2 = semimodel.getBuildingDesc(btypes[1])
        if b1.strip() == b2.strip():
            comment = fmt1 % (b1)
        else:
            regtext = fmt2 % (b1,b2)
    else:
        b1 = semimodel.getBuildingDesc(btypes[0])
        regtext = fmt1 % b1
    return default + '  ' + regtext

def get_secondary_hazards(expocat,mag):
    WAVETHRESH = .50
    fireevents = expocat.selectByHazard('fire')
    liquidevents = expocat.selectByHazard('liquefaction')
    slideevents = expocat.selectByHazard('landslide')
    waveevents = expocat.selectByHazard('tsunami')
    #get numbers of each type of secondary event
    nwaves = len(waveevents)
    nslides = len(slideevents)
    nfires = len(fireevents)
    nliquids = len(liquidevents)
    tmpevents = []
    wavedf = waveevents.getDataFrame()
    for index, event in wavedf.iterrows():
        if event['Waveheight'] >= WAVETHRESH:
            tmpevents.append(event)
    waveevents = tmpevents
    nsec = 0
    if len(fireevents):
        nsec += 1
    if len(waveevents):
        nsec += 1
    if len(liquidevents):
        nsec += 1
    if len(slideevents):
        nsec += 1
    hazards = []
    if nwaves and mag >= 7:
        hazards.append('tsunamis')
    if nslides:
        hazards.append('landslides')
    if nfires:
        hazards.append('fires')
    if nliquids:
        hazards.append('liquefaction')

    return hazards

def get_secondary_comment(lat,lon,mag):
    expocat = ExpoCat.fromDefault()
    expocat = expocat.selectByRadius(lat,lon,SEARCH_RADIUS)
    hazards = get_secondary_hazards(expocat,mag)
    if len(hazards) == 0:
        return ''

    nhazards = len(hazards)
    allhazardstrings = ['tsunamis','landslides','fires','liquefaction']

    sfmt = 'Recent earthquakes in this area have caused secondary hazards such as %s that might have contributed to losses.'
    if nhazards == 1:
        fstr = hazards[0]
    elif nhazards == 2:
        fstr = ' and '.join(hazards)
    elif nhazards == 3:
        fstr = ', '.join(hazards[0:1]) + 'and %s' % hazards[2]
    else:
        fstr = ', '.join(hazards[0:2]) + 'and %s' % hazards[3]

    hazcomm = sfmt % fstr
    return hazcomm

def get_historical_comment(lat,lon,mag,expodict,fatdict):
    default = """There were no earthquakes with significant population exposure to shaking within a 400 km radius of this event."""
    expocat = ExpoCat.fromDefault()
    expocat = expocat.selectByRadius(lat,lon,SEARCH_RADIUS)

    df = expocat.getDataFrame()

    #sort df by totaldeaths (inverse), then by maxmmmi, then by nmaxmmi.
    df = df.sort_values(['TotalDeaths','MaxMMI','NumMaxMMI'],ascending=False)
    
    if len(df) == 0:
        return default
    if len(df) >= 1:
        worst_event = df.iloc[0]
        desc = get_quake_desc(worst_event,lat,lon,True)
        return desc

def get_quake_desc(event,lat,lon,isMainEvent):
    ndeaths = event['TotalDeaths']
    #summarize the exposure values
    exposures = np.array([event['MMI1'],event['MMI2'],event['MMI3'],event['MMI4'],event['MMI5'],
                         event['MMI6'],event['MMI7'],event['MMI8'],event['MMI9+']])
    exposures = np.array([round_to_nearest(exp,1000) for exp in exposures])
    #get the highest two exposures greater than zero
    iexp = np.where(exposures > 0)[0][::-1]

    romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX or greater']
    if len(iexp) >= 2:
        exposures = [exposures[iexp[1]],exposures[iexp[0]]]
        ilevels = [romans[iexp[1]],romans[iexp[0]]]
        expfmt = ', with estimated population exposures of %s at intensity'
        expfmt = expfmt + ' %s and %s at intensity %s'
        exptxt = expfmt % (commify(int(exposures[0])),ilevels[0],commify(int(exposures[1])),ilevels[1])
    else:
        exptxt = ''

    #create string describing this most impactful event
    dfmt = 'A magnitude %.1f earthquake %i km %s of this event struck %s on %s (UTC)%s'

    mag = event['Magnitude']
    etime = event['Time'].strftime('%B %d, %Y')
    etime = re.sub(' 0',' ',etime)
    country = Country()
    if pd.isnull(event['Name']):
        if event['CountryCode'] == 'UM' and event['Lat'] > 40: #hack for persistent error in expocat
            cdict = country.getCountry('US')
        else:
            cdict = country.getCountry(event['CountryCode'])
        if cdict:
            cname = cdict['Name']
        else:
            cname = 'in the open ocean'
    else:
        cname = event['Name'].replace('"','')
        
    cdist = round(geodetic_distance(event['Lat'],event['Lon'],lat,lon))
    cdir = get_compass_dir(lat,lon,event['Lat'],event['Lon'],format='long').lower()
    if ndeaths and str(ndeaths) != "nan":
        dfmt = dfmt + ', resulting in a reported %s %s.'
        
        if ndeaths > 1:
            dstr = 'fatalities'
        else:
            dstr = 'fatality'

        ndeathstr = commify(int(ndeaths))
        eqdesc = dfmt % (mag,cdist,cdir,cname,etime,exptxt,ndeathstr,dstr)
    else:
        dfmt = dfmt + ', with no reported fatalities.'
        eqdesc = dfmt % (mag,cdist,cdir,cname,etime,exptxt)

    return eqdesc

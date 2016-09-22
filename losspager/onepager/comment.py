from scipy.special import erf
import numpy as np
from losspager.models.emploss import EmpiricalLoss
from losspager.models.econexposure import GDP
from losspager.utils.country import Country
from losspager.utils.mathutil import invphi
from impactutils.textformat.text import set_num_precision

GREEN_FAT_HIGH = 'There is a low likelihood of casualties.'
YELLOW_FAT_HIGH = '''Some casualties are possible and the impact should be relatively localized.
Past events with this alert level have required a local or regional level response.'''
ORANGE_FAT_HIGH = '''Significant casualties are likely and the disaster is potentially widespread.
Past events with this alert level have required a regional or national level response.'''
RED_FAT_HIGH = '''High casualties are probable and the disaster is likely widespread.
Past events with this alert level have required a national or international level response.'''

GREEN_ECON_HIGH = 'There is a low likelihood of damage.'
YELLOW_ECON_HIGH = '''Some damage is possible and the impact should be relatively localized. [GDPCOMMENT]
Past events with this alert level have required a local or regional level response.'''
ORANGE_ECON_HIGH = '''Significant damage is likely and the disaster is potentially widespread. [GDPCOMMENT]
Past events with this alert level have required a regional or national level response.'''
RED_ECON_HIGH = '''Extensive damage is probable and the disaster is likely widespread. [GDPCOMMENT]
 Past events with this alert level have required a national or international level response.'''

GREEN_FAT_LOW = 'There is a low likelihood of casualties.'
YELLOW_FAT_LOW = 'Some casualties are possible.'
ORANGE_FAT_LOW = 'Significant casualties are likely.'
RED_FAT_LOW = ''


GREEN_ECON_LOW = 'There is a low likelihood of damage.'
YELLOW_ECON_LOW = 'Some damage is possible. [GDPCOMMENT]'
ORANGE_ECON_LOW = 'Significant damage is likely. [GDPCOMMENT]'
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

def get_gdp_comment(ecodict,ecomodel,econexposure,event_year):
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
    gdp = gdp_obj.getGDP(dccode,event_year)
    country = Country()
    cinfo = country.getCountry(dccode)
    if cinfo is not None:
        pop = cinfo['Population']
    else:
        pop = 0
    T = (pop * gdp)/1e6
    if T == 0:
        return ''
    percent = erf(1/np.sqrt(2))
    plow = round(np.exp(np.log(expected)-eco_gvalue * invphi(percent)))
    phigh =round(np.exp(eco_gvalue * invphi(percent) + np.log(expected)))
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
        

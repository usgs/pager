#stdlib imports
from datetime import datetime
from textwrap import dedent

#third party imports
from impactutils.textformat.text import pop_round,dec_to_roman,pop_round_short

DATEFMT = '%Y/%m/%d-%H:%M'
MIN_POP = 1000

def generate_subject_line(version,pdata):
    # if update:
    #         subject = 'UPDATE: %s Alert, PAGER V%i %s' % (alertlevel,vnum,pagerversion.location)
    #     elif review:
    #         subject = 'Pending Alert, PAGER V%i %s' % (vnum,pagerversion.location)
    #     else:
    #         subject = '%s Alert, PAGER V%i %s' % (alertlevel,vnum,pagerversion.location)
    is_update = False
    if version.number > 1:
        event = version.event
        for tversion in event.versions:
            if len(tversion.addresses) > 0:
                is_update = True
                break

    alertlevel = pdata.summary_alert_pending
    vnum = version.number
    location = pdata.location
    
    if is_update:
        subject = 'UPDATE: %s Alert, PAGER V%i %s' % (alertlevel,vnum,location)
    else:
        subject = '%s Alert, PAGER V%i %s' % (alertlevel,vnum,location)
    return subject
        

def strip_leading_spaces(string):
    newlines = []
    for line in string.split('\n'):
        newline = line.lstrip()
        newlines.append(newline)
    newstring = '\n'.join(newlines)
    return newstring

def format_exposure(exposures,format,max_border_mmi):
    if format == 'short':
        #get the three highest exposures with 1,000 people or greater
        #format them as:
        #I6=19,000
        #I5=1,034,000
        expstr = 'No population exposure'
        if len(exposures):
            expstr = ''
            expohold = 0
            for mmi in range(10,0,-1):
                pop = 0
                expo = exposures[mmi-1]
                if mmi == 10:
                    expohold = expo
                elif mmi == 9:
                    pop = expo + expohold
                else:
                    pop = expo
                if pop >= MIN_POP:
                    popstr = pop_round(pop)
                    expstr += 'I%i=%s\n' % (mmi,popstr)
    else:
        #get the all  highest exposures with 1,000 people or greater
        #format them as:
        #MMI6 19,000
        #MMI5 1,034,000
        expstr = 'No population exposure'
        if len(exposures):
            expstr = ''
            expohold = 0
            for mmi in range(10,0,-1):
                pop = 0
                expo = exposures[mmi-1]
                if mmi == 10:
                    expohold = expo
                elif mmi == 9:
                    pop = expo + expohold
                else:
                    pop = expo
                if pop >= MIN_POP:
                    popstr = pop_round(pop)
                    flag = ''
                    if mmi < max_border_mmi:
                        flag = '*'
                    expstr += 'MMI%i %-8s%s\n' % (mmi,popstr,flag)
    return expstr

def format_city_table(cities):
    """Abbreviate a Pandas dataframe of city information

    Output should look like:
    MMI  City                           Population
    IV   Muisne                         13,393
    IV   Rosa Zarate                    42,121
    III  Pedernales                     5,983

    Input will a dataframe with columns: ccode iscap lat lon mmi name on_map pop

    :param cities:
      Pandas dataframe.
    :returns:
      String of city table info abbreviated for email delivery.
    """
    #name, mmi,pop
    fmt = '{mmi:5s} {city:30s} {pop:<10s}\n'
    city_table = ''
    city_table += fmt.format(mmi='MMI',city='City',pop='Population')
    for idx,city in cities.iterrows():
        mmiroman = dec_to_roman(city['mmi'])
        city_table += fmt.format(mmi=mmiroman,
                                 city=city['name'],
                                 pop=pop_round(city['pop']))
    #city_table = dedent(city_table)
    
    return city_table

def format_earthquakes(histquakes):
    #distance,date,magnitude,maxmmi,maxmmiexp,deaths
    tablestr = ''
    hdr = '{date:16s} {dist:10s} {mag:4s} {mmi:10s} {deaths:14s}\n'
    hdr = hdr.format(date='Date (UTC)',
                     dist='Dist. (km)',
                     mag='Mag.',
                     mmi='Max MMI(#)',
                     deaths='Shaking Deaths')
    tablestr += hdr
    fmt = '{date:16s} {dist:10d} {mag:4.1f} {mmi:10s} {deaths:14s}\n'
    for histquake in histquakes:
        eqtime = datetime.strptime(histquake['Time'],'%Y-%m-%d %H:%M:%S')
        datestr = eqtime.strftime(DATEFMT)
        mmistr = '{}({})'.format(dec_to_roman(histquake['MaxMMI']),
                                 pop_round_short(histquake['NumMaxMMI']))
        line = fmt.format(date=datestr,
                          dist=int(histquake['Distance']),
                          mag=histquake['Magnitude'],
                          mmi=mmistr,
                          deaths=pop_round_short(histquake['TotalDeaths']))
        tablestr += line

    return tablestr

def format_short(version,expstr):
    #using python string .format() method with brackets
    msg = '''
    M{magnitude:.1f}
    D{depth:d}
    {time}
    ({lat:.3f},{lon:.3f})
    ALERT:{summarylevel}
    '''.format(magnitude=version.magnitude,
               depth=int(version.depth),
               time=version.time.strftime(DATEFMT),
               lat=version.lat,
               lon=version.lon,
               summarylevel=version.summarylevel.capitalize())
    msg = dedent(msg)
    msg += expstr
    return msg

def format_long(version,pdata,expstr,event_url):
    tsunami_comment = ''
    eventinfo = pdata.getEventInfo()
    if eventinfo['tsunami']:
        tsunami_comment = 'FOR TSUNAMI INFORMATION, SEE: tsunami.gov'
    cityinfo = pdata._pagerdict['city_table']
    city_table = format_city_table(cityinfo)
    historical_earthquakes = format_earthquakes(pdata.getHistoricalTable())
    first,second = pdata.getImpactComments()
    impact_comment = first + ' ' + second
    msg = '''
    PAGER Version: {version:d}
    {location}
    GMT: {time}
    MAG: {mag:.1f}
    LAT: {lat:.3f}
    LON: {lon:.3f}
    DEP: {depth:d}
    ID: {eventid}

    Alert Level: {summary_level}
    {impact_comment}

    {tsunami_comment}

    Estimated Population Exposure
    {expstr}

    * - MMI level extends beyond map boundary, actual population exposure may be larger.

    {city_table}

    Structures:
    {structure_comment}

    Historical Earthquakes:
    {historical_earthquakes}
    {secondary_comment}
    {url}
    '''.format(version=version.number,
               location=eventinfo['location'],
               time=version.time.strftime(DATEFMT),
               mag=version.magnitude,
               lat=version.lat,
               lon=version.lon,
               depth=int(version.depth),
               eventid=version.versioncode,
               summary_level=version.summarylevel.capitalize(),
               impact_comment=impact_comment,
               tsunami_comment=tsunami_comment,
               expstr=expstr,
               city_table=city_table,
               structure_comment=pdata.getStructureComment,
               historical_earthquakes=historical_earthquakes,
               secondary_comment=pdata.getSecondaryComment,
               url=event_url)
    msg = strip_leading_spaces(msg)
    return msg

def format_msg(version,pdata,format,event_url):
    """Create an email message text for either short or long format.

    :param version:
      EmailSchema.Version instance.
    :param pdata:
      PagerData instance.
    :param format:
      One of 'short' or 'long'.
    :returns:
      email text formatted for SMS (short) or email (long) messages. 
    """
    #TODO - expose this in pagerdata somehow so we're not reaching into its guts
    max_border_mmi = pdata._pagerdict['population_exposure']['maximum_border_mmi']
    expstr = format_exposure(pdata.getTotalExposure(),format,max_border_mmi)
    if format == 'short':
        msg = format_short(version,expstr)
    else:
        msg = format_long(version,pdata,expstr,event_url)
    return msg
        

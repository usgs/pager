from textwrap import dedent
from impactutils.textformat.text import pop_round,dec_to_roman,pop_round_short

DATEFMT = '%Y/%m/%d-%H:%M'
MIN_POP = 1000

def strip_leading_spaces(string):
    newlines = []
    for line in string.split('\n'):
        newline = line.lstrip()
        newlines.append(newline)
    newstring = '\n'.join(newlines)
    return newstring

def format_exposure(exposures,format):
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
                expo = exposures[mmi-1]
                if mmi == 10:
                    expohold = expo['exposure']
                if mmi == 9:
                    pop = expo['exposure'] + expohold
                else:
                    pop = expo['exposure']
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
                expo = exposures[mmi-1]
                if mmi == 10:
                    expohold = expo['exposure']
                if mmi == 9:
                    pop = expo['exposure'] + expohold
                else:
                    pop = expo['exposure']
                if pop >= MIN_POP:
                    popstr = pop_round(pop)
                    flag = ''
                    if expo['inside']:
                        flag = '*'
                    expstr += 'MMI%i %-8s%s\n' % (mmi,popstr,flag)
    return expstr

def format_city_table(cities):
    #name, mmi,pop
    fmt = '{mmi:5s} {city:30s} {pop:<10s}\n'
    city_table = ''
    city_table += fmt.format(mmi='MMI',city='City',pop='Population')
    for city in cities:
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
        datestr = histquake['date'].strftime(DATEFMT)
        mmistr = '{}({})'.format(dec_to_roman(histquake['maxmmi']),
                                 pop_round_short(histquake['maxmmiexp']))
        line = fmt.format(date=datestr,
                          dist=int(histquake['distance']),
                          mag=histquake['magnitude'],
                          mmi=mmistr,
                          deaths=pop_round_short(histquake['deaths']))
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

def format_long(version,eventinfo,expstr):
    tsunami_comment = ''
    if eventinfo['tsunami']:
        tsunami_comment = 'FOR TSUNAMI INFORMATION, SEE: tsunami.gov'
    city_table = format_city_table(eventinfo['cities'])
    historical_earthquakes = format_earthquakes(eventinfo['historical_earthquakes'])
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
               impact_comment=eventinfo['impact_comment'],
               tsunami_comment=tsunami_comment,
               expstr=expstr,
               city_table=city_table,
               structure_comment=eventinfo['structure_comment'],
               historical_earthquakes=historical_earthquakes,
               secondary_comment=eventinfo['secondary_comment'],
               url=eventinfo['url'])
    msg = strip_leading_spaces(msg)
    return msg

def format_msg(version,eventinfo,format):
    expstr = format_exposure(eventinfo['exposures'],format)
    if format == 'short':
        msg = format_short(version,expstr)
    else:
        msg = format_long(version,eventinfo,expstr)
    return msg
        

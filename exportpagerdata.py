#!/usr/bin/env python

import MySQLdb as mysql
import json
import numpy
import io
from xml.dom import minidom
import numpy as np
import sys
from datetime import datetime
import argparse

def getRandomName(wordlist,is_org=False):
    idx1 = np.random.randint(len(wordlist))
    idx2 = np.random.randint(len(wordlist))
    word1 = wordlist[idx1].capitalize()
    word2 = wordlist[idx2].capitalize()
    if is_org:
        rname = ('Institute of %s %s' % (word1,word2),word1[0]+word2[0])
    else:
        rname = (wordlist[idx1].capitalize(),wordlist[idx2].capitalize())
    return rname

def getGroupName(cursor,groupid):
    query = 'SELECT groupname FROM regiongroup WHERE id=%i' % groupid
    cursor.execute(query)
    groupname = cursor.fetchone()[0]
    return groupname

def getUserOrg(cursor,orgid):
    query = 'SELECT shortname FROM organization WHERE id=%i' % orgid
    cursor.execute(query)
    org = cursor.fetchone()[0]
    return org

def getOrgs(cursor,wordlist,anonymize=False):
    query = 'SELECT name,shortname FROM organization'
    cursor.execute(query)
    orglist = []
    for row in cursor.fetchall():
        if anonymize:
            name,shortname = getRandomName(wordlist,is_org=True)
        else:
            name,shortname = row[0].strip(),row[1].strip()
        oid = row[0]
        orglist.append({'name':name,'shortname':shortname})
    return orglist

def getGroups(cursor):
    query = 'SELECT name,displaytext FROM pgroup'
    cursor.execute(query)
    grouplist = []
    for row in cursor.fetchall():
        grouplist.append({'name':row[0],'displaytext':row[1]})
    return grouplist

def readPolyKML(polystr):
    root = minidom.parseString(polystr)
    polygons = root.getElementsByTagName('Polygon')
    x = []
    y = []
    for polygon in polygons:
        coord = polygon.getElementsByTagName('coordinates')[0]
        cdata = coord.firstChild.data
        plines = cdata.split()
        segment = []
        for p in plines:
            xt,yt,zt = p.split(',')
            xt = float(xt)
            yt = float(yt)
            x.append(xt)
            y.append(yt)
        x.append(float('nan'))
        y.append(float('nan'))
    root.unlink()

    return x,y

def getRegions(cursor):
    polydict = {} #dictionary of {'code':(x,y)} where x and y are NaN separated arrays denoting multi-part polygons
    cursor.execute('SELECT code,polykml,regiongroup_id FROM region')
    rows = cursor.fetchall()
    for row in rows:
        code = row[0]
        polystr = row[1]
        groupid = row[2]

        #get the group name
        cursor.execute('SELECT groupname FROM regiongroup WHERE id="%i"' % groupid)
        groupname = cursor.fetchone()[0]

        groupname = groupname.strip().replace(' ','_')
        code = groupname + '-' + code
        print('Getting region %s' % code)
        
        x,y = readPolyKML(polystr)

        polyarrays = []
        x = np.array(x)
        y = np.array(y)
        inan = np.where(np.isnan(x))[0]
        start = 0
        for i in range(0,len(inan)):
            xseg = x[start:inan[i]].tolist()
            yseg = y[start:inan[i]].tolist()
            xy = list(zip(xseg,yseg))
            polyarrays.append(xy)
            start = inan[i]+1
        
        geojson = {'type':'Feature',
                   'geometry':{'type':'Polygon',
                               'coordinates':polyarrays},
                    'properties':{'code':code}}
                               
        polydict[code] = geojson

    return polydict

def getUsers(cursor,wordlist,orgs,anonymize=False,nusers=None):
    totalquery = 'SELECT count(*) from user';
    cursor.execute(totalquery)
    ntotalusers = cursor.fetchone()[0]
    if nusers is None:
        nusers = ntotalusers
    userquery = 'SELECT id,org_id,firstname,lastname,createdon FROM user LIMIT %i' % nusers
    cursor.execute(userquery)
    user_rows = cursor.fetchall()
    users = []
    for urow in user_rows:
        uid,org_id,firstname,lastname,createdon = urow
        
        if anonymize:
            lastname,firstname = getRandomName(wordlist)
            for torg in orgs:
                if torg['id'] == org_id:
                    org = torg['shortname'].strip()
                    break
        else:
            if org_id is not None:
                org = getUserOrg(cursor,org_id)
            else:
                org = 'None'    
        
        emailquery = 'SELECT id,email,isprimary,priority FROM address WHERE user_id = %i' % uid
        cursor.execute(emailquery)
        email_rows = cursor.fetchall()
        
        emails = []
        for erow in email_rows:
            eid,email,isprimary,priority = erow

            if anonymize:
                email = '%s.%s-%i@bogusmail.org' % (firstname,lastname,eid)
            
            profilequery = 'SELECT id,format_id FROM profile WHERE address_id=%i' % eid
            cursor.execute(profilequery)
            profile_rows = cursor.fetchall()
            profiles = []
            for prow in profile_rows:
                pid,formatid = prow
                #get the regions for this profile
                regionidquery = 'SELECT region_id FROM profile_region_bridge WHERE profile_id=%i' % pid
                cursor.execute(regionidquery)
                regionid_rows = cursor.fetchall()
                regioncodes = []
                for regionid in regionid_rows:
                    regionquery = 'SELECT code,regiongroup_id FROM region where id=%i' % regionid
                    cursor.execute(regionquery)
                    regionrow = cursor.fetchone()
                    code = regionrow[0]
                    groupid = regionrow[1]
                    groupname = getGroupName(cursor,groupid)
                    regioncode = groupname.strip().replace(' ','_') + '-' + code
                    regioncodes.append({'name':regioncode})
                #get the threshold(s) for this profile
                threshquery = 'SELECT alertscheme_id,value FROM threshold WHERE profile_id=%i' % pid
                cursor.execute(threshquery)
                threshrows = cursor.fetchall()
                thresholds = []
                for threshrow in threshrows:
                    aid,threshold = threshrow
                    schemequery = 'SELECT name FROM alertscheme WHERE id=%i' % aid
                    cursor.execute(schemequery)
                    scheme = cursor.fetchone()[0]
                    thresholds.append({'alertscheme':scheme,'value':threshold})
                #get the format for this profile
                formatquery = 'SELECT name FROM format WHERE id=%i' % formatid
                cursor.execute(formatquery)
                emailformat = cursor.fetchone()[0]
                emailformat = emailformat.replace('expo','')
                profiles.append({'thresholds':thresholds[:],
                                 'regions':regioncodes[:]})
            
            emails.append({'email':email,
                           'priority':priority,
                           'is_primary':isprimary,
                           'format':emailformat,
                           'profiles':profiles[:]})

        
        users.append({'lastname':lastname,
                      'firstname':firstname,
                      'addresses':emails,
                      'createdon':createdon.strftime('%Y-%m-%d %H:%M:%S'),
                      'org':org})
    return users

def getEvents(cursor):
    query = 'SELECT id,eventcode FROM event'
    cursor.execute(query)
    events = []
    for row in cursor.fetchall():
        event = {}
        eid = row[0]
        ecode = row[1]
        cols = ['id','versioncode','network',
                'number','time','lat','lon',
                'depth','mag','maxmmi','processtime',
                'summarylevel']
        colstr = ','.join(cols)
        query2 = 'SELECT %s FROM version WHERE event_id=%i' % (colstr,eid)
        cursor.execute(query2)
        vrows = cursor.fetchall()
        versions = []
        for vrow in vrows:
            version = {}
            for i in range(0,len(cols)):
                col = cols[i]
                value = vrow[i]
                if isinstance(value,datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                version[col] = value
            versions.append(version)
        event['id'] = eid
        event['eventcode'] = ecode
        event['versions'] = versions
        events.append(event)
    return events

def getVersionAddress(cursor):
    bridge = []
    query = 'SELECT version_id,address_id FROM version_address_bridge'
    cursor.execute(query)
    for row in cursor.fetchall():
        bridge.append(row)
    return bridge

def main(args):
    db = mysql.connect(host='localhost',db='losspager',user=args.user,passwd=args.password)
    cursor = db.cursor()
    allwords = open('/usr/share/dict/words','rt').readlines()
    wordlist = []
    for word in allwords:
        word = word.strip()
        if len(word) > 3:
            wordlist.append(word)

    orgs = getOrgs(cursor,wordlist,anonymize=pargs.anonymize)
    users = getUsers(cursor,wordlist,orgs,nusers=pargs.limit_users,anonymize=pargs.anonymize)
    regions = getRegions(cursor)
    
    groups = getGroups(cursor)
    events = getEvents(cursor)
    bridge = getVersionAddress(cursor)

    #write out a file containing user information
    userfile = args.basefile + '_users.json'
    f = open(userfile,'wt')
    jstr = json.dumps(users,indent=2)
    f.write(jstr)
    f.close()

    #write out a file containing organization information
    orgfile = args.basefile + '_orgs.json'
    f = open(orgfile,'wt')
    jstr = json.dumps(orgs,indent=2)
    f.write(jstr)
    f.close()
    
    
    # database = {'users':users,'regions':regions,'orgs':orgs,
    #             'groups':groups,'version_address':bridge,
    #             'events':events}
    # jstr = json.dumps(database)
    # f = open(args.jsonfile,'wt')
    # f.write(jstr)
    # f.close()
    cursor.close()
    db.close()
    
if __name__ == '__main__':
    desc = 'Export PAGER users, regions, events, etc. from MySQL database into multiple JSON files.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('basefile', help='Specify base output JSON file name')
    parser.add_argument('user', help='Specify PAGER user for MySQL DB')
    parser.add_argument('password', help='Specify PAGER password for MySQL DB')
    parser.add_argument('-a','--anonymize', action='store_true',default=False,
                        help='Anonymize users and organizations')
    parser.add_argument('-l','--limit-users', type=int, default=None,
                        help='Limit the users extracted to desired number.')

    pargs = parser.parse_args()
    main(pargs)    
        
    


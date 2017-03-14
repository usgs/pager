#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys
import json
from datetime import datetime
import shutil

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry.point import Point

#local imports
import sqlalchemy
from losspager.schema import emailschema
from losspager.utils.datapath import get_data_path

NUSERS = 10

DATEFMT = '%Y-%m-%d %H:%M:%S'

def test_create_db(userfile=None,orgfile=None):
    memurl = 'sqlite://'
    #create a user in a dictionary
    threshold = {'alertscheme':'eis',
                 'value':'red'}
    region = {'name':'UNSOUEU'}
    profile = {'regions':[region],
               'thresholds':[threshold]}
    address = {'email':'lex@luthorcorp.com',
               'is_primary':True,
               'priority':1,
               'format':'long',
               'profiles':[profile]}
    userdict = {'lastname':'Luthor',
                'firstname':'Alexander',
                'createdon':datetime.utcnow().strftime(emailschema.TIME_FORMAT),
                'org':'USGS',
                'addresses':[address]}
    tdir = tempfile.mkdtemp()
    if userfile is None:
        userfile = os.path.join(tdir,'users.json')
        f = open(userfile,'wt')
        users = [userdict]
        json.dump(users,f)
        f.close()
    try:
        schemadir = get_data_path('schema')
        session = emailschema.create_db(memurl,schemadir,users_jsonfile=userfile,orgs_jsonfile=orgfile)
        print('Testing contents of in-memory database...')
        assert session.query(emailschema.User).count() == 1
        assert session.query(emailschema.Region).count() == 47
        print('Passed test.')
    except:
        shutil.rmtree(tdir)


def test_region_serialization():
    memurl = 'sqlite://'
    schemadir = get_data_path('schema')
    session = emailschema.create_db(memurl,schemadir)

    ca_coords = [[[-125.771484,41.957448],
                  [-112.412109,42.672339],
                  [-112.060547,31.791221],
                  [-126.298828,31.416944],
                  [-125.771484,41.957448]]]
                  
    lon,lat = (-119.443359,37.149371)
    regiondict = {'type':'Feature',
                  'properties':{'code':'US_States-California',
                                'desc':'California'},
                  'geometry': {'type':'Polygon',
                  'coordinates':ca_coords}}
    

    region = emailschema.Region()
    region.fromDict(session,regiondict)
    assert region.containsPoint(lat,lon) == True
    
    regiondict2 = region.toDict()
    assert regiondict == regiondict2
    
    session.close()

def test_user_serialization():
    memurl = 'sqlite://'
    schemadir = get_data_path('schema')
    session = emailschema.create_db(memurl,schemadir)

    #create a user in a dictionary
    threshold = {'alertscheme':'eis',
                 'value':'red'}
    region = {'name':'UN_Regions-UNSOUEU'}
    profile = {'regions':[region],
               'thresholds':[threshold]}
    address = {'email':'lex@luthorcorp.com',
               'is_primary':True,
               'priority':1,
               'format':'long',
               'profiles':[profile]}
    userdict = {'lastname':'Luthor',
                'firstname':'Alexander',
                'createdon':datetime.utcnow().strftime(emailschema.TIME_FORMAT),
                'org':'USGS',
                'addresses':[address]}
    
    user = emailschema.User()
    #inflate the user from the dictionary
    user.fromDict(session,userdict)

    #deflate the user into a dictionary
    userdict2 = user.toDict()

    #make sure the input/output dictionaries have the same content
    assert userdict['lastname'] == userdict2['lastname']
    assert userdict['firstname'] == userdict2['firstname']
    assert userdict['createdon'] == userdict2['createdon']
    assert userdict['org'] == userdict2['org']

    assert userdict['addresses'][0]['email'] == userdict2['addresses'][0]['email']
    assert userdict['addresses'][0]['is_primary'] == userdict2['addresses'][0]['is_primary']
    assert userdict['addresses'][0]['priority'] == userdict2['addresses'][0]['priority']
    assert userdict['addresses'][0]['format'] == userdict2['addresses'][0]['format']

    rname = userdict['addresses'][0]['profiles'][0]['regions'][0]['name']
    rname2 = userdict2['addresses'][0]['profiles'][0]['regions'][0]['name']
    assert rname == rname2

    tname = userdict['addresses'][0]['profiles'][0]['thresholds'][0]['alertscheme']
    tname2 = userdict2['addresses'][0]['profiles'][0]['thresholds'][0]['alertscheme']
    assert tname == tname2

    tvalue = userdict['addresses'][0]['profiles'][0]['thresholds'][0]['value']
    tvalue2 = userdict2['addresses'][0]['profiles'][0]['thresholds'][0]['value']
    assert tvalue == tvalue2
    
    session.close()

def test_get_polygon():
    memurl = 'sqlite://'
    schemadir = get_data_path('schema')
    session = emailschema.create_db(memurl,schemadir)

    POINTS = {'UNEASTAFR':[(-18.319329,36.408691)],
              'UNNORAFR':[(29.051368,20.478516)],
              'UNWESTAS':[(23.216107,45.263672)],
              'UNWESTAFR':[(10.806328,-11.513672)],
              'UNSEAS':[(1.202915,116.279297)],
              'UNNOREU':[(61.76013,14.853516)],
              'UNCENTAMER':[(11.817621,-84.177246)],
              'UNMIC':[(13.444304,144.793731)],
              'UNMIDAFR':[(-9.115656,17.094727)],
              'UNSOUAMER':[(-21.314964,-59.150391)],
              'UNSOUEU':[(40.101185,-2.504883)],
              'UNWESTEU':[(47.567261,3.999023)],
              'UNMEL':[(-9.975613,149.128418)],
              'UNAUSNZ':[(-23.427969,134.912109)],
              'UNCARIB':[(18.847812,-70.466309)],
              'UNSOUAFR':[(-31.814563,24.038086)],
              'UNEASTEU':[(50.392761,25.708008)],
              'UNEASTAS':[(29.59973,111.577148)],
              'UNNORAMER':[(38.505191,-100.019531)],
              'UNCENTAS':[(40.033924,66.225586)],
              'UNSOUAS':[(14.067317,77.607422)],
              'UNPOL':[(-21.178986,-175.198242)],
              'FEMA01':[(44.585577,-69.147949)],
              'FEMA05':[(46.342188,-88.791504)],
              'FEMA10':[(44.80425,-120.651855),(65.924072,-151.347656)],
              'FEMA07':[(38.577158,-97.668457)],
              'FEMA02':[(42.645071,-74.992676)],
              'FEMA08':[(43.384092,-107.556152)],
              'FEMA09':[(37.434522,-120.695801),(13.444304,144.793731),(-14.30164,-170.696181)],
              'FEMA03':[(37.747915,-78.112793)],
              'FEMA06':[(30.215168,-98.195801)],
              'FEMA04':[(33.703207,-84.276123)],
              'SWAN':[(22.093275,-4.262695),(-29.71191,21.181641)],
              'LAC':[(-26.613086,-61.083984)],
              'EAP':[(-28.042895,140.449219),(-17.751956,-149.315186)],
              'SA':[(17.595594,76.311035)],
              'ECA':[(6.389001,42.84668)],
              'EMCA':[(49.772396,16.479492),(55.463285,-105.732422)],
              'Cont_US':[(37.974515,-104.501953)],
              'US_Terr':[(19.639354,-155.577393)],
              'Not_US':[(-10.541821,25.136719)],
              'USNORTHCOM':[(25.433353,-103.535156)],
              'USEUCOM':[(51.940032,10.700684)],
              'USPACOM':[(21.441245,-157.922974)],
              'USSOUTHCOM':[(-1.331972,-60.073242)],
              'USAFRICOM':[(14.551684,21.269531)],
              'USCENTCOM':[(21.767152,49.350586)]}

    for regioncode,plist in POINTS.items():
        region = session.query(emailschema.Region).filter(emailschema.Region.name == regioncode).first()
        if region is None:
            raise Exception('Could not find region %s in database!' % regioncode)
        for point in plist:
            lat,lon = point
            print('Checking region %s...' % regioncode)
            if not region.containsPoint(lat,lon):
                raise Exception('Region %s does not contain point (%.4f,%.4f).' % (regioncode,lat,lon))

    session.close()

def test_delete_cascade():
    memurl = 'sqlite://'
    schemadir = get_data_path('schema')
    session = emailschema.create_db(memurl,schemadir)

    #create a user in a dictionary
    threshold = {'alertscheme':'eis',
                 'value':'red'}
    region = {'name':'UN_Regions-UNSOUEU'}
    profile = {'regions':[region],
               'thresholds':[threshold]}
    address = {'email':'lex@luthorcorp.com',
               'is_primary':True,
               'priority':1,
               'format':'long',
               'profiles':[profile]}
    userdict = {'lastname':'Luthor',
                'firstname':'Alexander',
                'createdon':datetime.utcnow().strftime(emailschema.TIME_FORMAT),
                'org':'USGS',
                'addresses':[address]}

    users_before_add = session.query(emailschema.User).count()
    addresses_before_add = session.query(emailschema.Address).count()
    print('Testing deleting users...')
    assert users_before_add == 0
    assert addresses_before_add == 0
    print('No users before insert.')
    user = emailschema.User()
    #inflate the user from the dictionary
    user.fromDict(session,userdict)
    session.add(user)
    users_after_add = session.query(emailschema.User).count()
    addresses_after_add = session.query(emailschema.Address).count()
    assert users_after_add == 1
    assert addresses_after_add == 1
    print('One user, one address after insert.')
    session.delete(user)
    session.commit()
    users_after_delete = session.query(emailschema.User).count()
    addresses_after_delete = session.query(emailschema.Address).count()
    assert users_after_delete == 0
    assert addresses_after_delete == 0
    print('No users, no addresses after deleting user.')


    #test deleting cascades with events
    event = emailschema.Event(eventcode='us2017abcd')
    version = emailschema.Version(versioncode='us2017abcd',
                                  time=datetime.utcnow(),
                                  country='US',
                                  lat=34.15,
                                  lon=-118.13,
                                  depth=10.0,
                                  magnitude=6.5,
                                  number=1,
                                  fatlevel=1,
                                  ecolevel=2,
                                  summarylevel=2,
                                  processtime=datetime.utcnow(),
                                  maxmmi=7.1)

    print('Test cascade deletes with events and versions...')
    events_before_add = session.query(emailschema.Event).count()
    versions_before_add = session.query(emailschema.Version).count()
    assert events_before_add == 0
    assert versions_before_add == 0
    
    event.versions.append(version)
    session.add(event)

    events_after_add = session.query(emailschema.Event).count()
    versions_after_add = session.query(emailschema.Version).count()

    assert events_after_add == 1
    assert versions_after_add == 1

    session.delete(event)
    
    events_after_delete = session.query(emailschema.Event).count()
    versions_after_delete = session.query(emailschema.Version).count()

    assert events_after_delete == 0
    assert versions_after_delete == 0
    
    session.close()
   
# def test_get_email():
#     dbfile = os.path.abspath(os.path.join(homedir,'..','data','losspager_test.db'))
#     url = 'sqlite:///%s' % dbfile
#     session = emailschema.get_session(url)
#     version = emailschema.Version(versioncode='us1234abcd',
#                                   time=datetime.utcnow(),
#                                   lat = 37.761351,
#                                   lon = -122.395935,
#                                   depth = 10.0,
#                                   magnitude=7.5,
#                                   number=1,
#                                   maxmmi = 7.4,
#                                   summarylevel='yellow')
#     test_num_addresses = 9
#     naddresses = 0
#     for address in session.query(emailschema.Address):
#         if address.shouldAlert(version):
#             naddresses += 1
#             # print(address)
#             # for profile in address.profiles:
#             #     print('\tProfile %s' % str(profile))
#             #     for threshold in profile.thresholds:
#             #         print('\t\t'+str(threshold))
#     assert test_num_addresses == naddresses
    
if __name__ == '__main__':
    userfile = None
    orgfile = None
    if len(sys.argv) > 1:
        userfile = sys.argv[1]
    if len(sys.argv) > 2:
        orgfile = sys.argv[2]
    
    test_create_db(userfile=userfile,orgfile=orgfile)
    test_region_serialization()
    test_user_serialization()
    test_get_polygon()
    test_delete_cascade()
    # test_get_email()

    

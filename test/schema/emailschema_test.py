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
from mpl_toolkits.basemap import Basemap

#local imports
import sqlalchemy
from losspager.schema import emailschema

NUSERS = 10

def test_create_db():
    #TODO change this to memory url
    tempdir = None
    try:
        
        #Create a sqlite file database engine
        tempdir = tempfile.mkdtemp()
        tmpfile = os.path.abspath(os.path.join(tempdir,'test_data.db'))
        fileurl = 'sqlite:///%s' % tmpfile
        jsonfile = os.path.join(homedir,'..','data','pager_profiles.json')
        session = emailschema.create_db(fileurl,jsonfile,nusers=10,create_db=True)
        print('Checking to see that database has expected number of users.')
        assert len(session.query(emailschema.User).all()) == 10
        print('Database has 10 users in it.')
        hasregions = False
        for user in session.query(emailschema.User):
            for address in user.addresses:
                if len(address.regions):
                    hasregions = True
                    break
        session.close()
        x = 1
    except Exception as error:
        raise error
    finally:
        if os.path.isdir(tempdir):
            shutil.rmtree(tempdir)

def test_read_db():
    dbfile = os.path.abspath(os.path.join(homedir,'..','data','losspager_test.db'))
    url = 'sqlite:///%s' % dbfile
    session = emailschema.get_session(url)
    assert len(session.query(emailschema.User).all()) == 510

def test_get_polygon():
    dbfile = os.path.abspath(os.path.join(homedir,'..','data','losspager_test.db'))
    url = 'sqlite:///%s' % dbfile
    session = emailschema.get_session(url)
    for region in session.query(emailschema.Region):
        polygon = region.getPolygon()
    session.close()

   
def test_get_email():
    dbfile = os.path.abspath(os.path.join(homedir,'..','data','losspager_test.db'))
    url = 'sqlite:///%s' % dbfile
    session = emailschema.get_session(url)
    version = emailschema.Version(versioncode='us1234abcd',
                                  time=datetime.utcnow(),
                                  lat = 37.761351,
                                  lon = -122.395935,
                                  depth = 10.0,
                                  magnitude=7.5,
                                  number=1,
                                  maxmmi = 7.4,
                                  summarylevel='yellow')
    for address in session.query(emailschema.Address):
        if address.shouldAlert(version):
            print(address)
            for threshold in address.thresholds:
                print('\t'+str(threshold))

    
if __name__ == '__main__':
    #test_get_polygon()
    tmpfile = '/Users/mhearne/src/python/all_pager_users.db'
    fileurl = 'sqlite:///%s' % tmpfile
    jsonfile = os.path.join('/Users/mhearne/src/python/','pager_profiles.json')
    session = emailschema.create_db(fileurl,jsonfile,nusers=None,create_db=True)
    session.close()
    sys.exit(0)
    # test_read_db()
    # test_get_email()
    #test_create_db()

    

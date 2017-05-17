#!/usr/bin/env python

#stdlib imports
from datetime import datetime,timedelta
import enum
import sys
import json
import io
import os

#third-party imports
import numpy as np
from shapely.geometry import Polygon, Point, shape
from openquake.hazardlib.geo.utils import get_orthographic_projection
import pyproj

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table, Integer, String, DateTime, Boolean, Float, LargeBinary, Enum
from sqlalchemy.orm import sessionmaker
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates

from sqlalchemy_utils import database_exists,create_database

#local imports
from losspager.utils.exception import PagerException

#constants
MAX_ELAPSED_SECONDS = 8*3600
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_EIS_LEVELS = 2


#We dynamically (not sure why?) create the base class for our objects
Base = declarative_base()

"""Relational Database schema and code for managing PAGER users and their profiles.

"""

class GeoThing(object):
    def __init__(self, d):
        self.__geo_interface__ = d

#create our bridge tables here

#link the address and region tables
address_region_bridge = Table('address_region_bridge', Base.metadata,
                             Column('address_id', Integer, ForeignKey('address.id')),
                             Column('region_id', Integer, ForeignKey('region.id')))

#link the version and address tables 
#sendtime column keeps track of who got notified about what when
version_address_bridge = Table('version_address_bridge', Base.metadata,
                               Column('version_id', Integer, ForeignKey('version.id')),
                               Column('address_id', Integer, ForeignKey('address.id')),
                               Column('sendtime',DateTime))

profile_region_bridge = Table('profile_region_bridge',Base.metadata,
                               Column('profile_id', Integer, ForeignKey('profile.id')),
                               Column('region_id', Integer, ForeignKey('region.id')))

class _AlertEnum(enum.Enum):
    """Simple enum class for alert levels.
    """
    green = 0
    yellow = 1
    orange = 2
    red = 3

class User(Base):
    """Class representing a PAGER user.
    
    Relationship descriptions:
    - A User can have many Addresses.
    - A User can belong to one Organization.
    
    """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    lastname = Column(String)
    firstname = Column(String)
    createdon = Column(DateTime)
    organization_id = Column(Integer, ForeignKey('organization.id'))

    #A User can have many addresses
    addresses = relationship("Address", back_populates="user",cascade="all, delete, delete-orphan")

    #A user can belong to one organization
    organization = relationship("Organization", back_populates="users")
    ##This constructor is not being recognized by Python.  It used to be...???
    # def __init__(self,createdon=None):
    #     """
    #     :param createdon:
    #       UTC datetime object when user was added to the system.
    #     """
    #     if createdon is None:
    #         self.createdon = datetime.utcnow()
    #     else:
    #         self.createdon = createdon
    #     self.lastname = ''
    #     self.firstname = ''

    def __repr__(self):
        fmt = "<User(id=%i,name='%s %s', created='%s')>"
        tpl = (self.id,self.firstname,self.lastname,str(self.createdon))
        return fmt % tpl

    def fromDict(self,session,userdict):
        reqfields = set(['lastname','firstname','createdon','org','addresses'])
        if reqfields <= set(userdict.keys()):
            pass
        else:
            missing = list(reqfields - set(userdict.keys()))
            raise PagerException('Missing required fields for user: %s' % str(missing))
        #set the user fields
        self.lastname = userdict['lastname']
        self.firstname = userdict['firstname']
        self.createdon = datetime.strptime(userdict['createdon'],TIME_FORMAT) #will this be a string or a datetime?
        org = session.query(Organization).filter(Organization.shortname == userdict['org']).first()
        if org is None:
            raise PagerException('No organization named %s exists in the database.' % userdict['org'])
        self.organization = org
        self.addresses = []

        for addressdict in userdict['addresses']:
            address = Address()
            address.fromDict(session,addressdict)
            self.addresses.append(address)
        #first add this user to the session
        session.add(self)
        #then commit all the changes
        session.commit()

    def toDict(self):
        userdict = {'lastname':self.lastname,
                    'firstname':self.firstname,
                    'createdon':self.createdon.strftime(TIME_FORMAT),
                    'org':self.organization.shortname}

        addresses = []
        for address in self.addresses:
            adict = address.toDict()
            addresses.append(adict)
        userdict['addresses'] = addresses
        return userdict

class Address(Base):
    """Class representing a PAGER address.
    
    Relationship descriptions:
    - An Address has one User.
    - An Address can have many Versions.
    - An Address can have many Thresholds.
    - An Address can have many Regions.
    
    """
    __tablename__ = 'address'
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'),nullable=False)
    is_primary = Column(Boolean,nullable=False)
    #a low priority (i.e., 1) means this address should be emailed before addresses with higher numbers.
    priority = Column(Integer, nullable=False)
    format = Column(String,nullable=False)

    #A user can have many addresses
    user = relationship("User", back_populates="addresses")

    #An address can have many versions
    versions = relationship(
        "Version",
        secondary=version_address_bridge,
        back_populates="addresses")

    #An address can have many thresholds
    profiles = relationship("Profile",back_populates="address")
    
    def __repr__(self):
        return "<Address(email='%s')>" % self.email

    def shouldAlert(self,version,renotify=False,release=False,ignore_time_limit=False):
        """Determine whether an alert should be sent to this address for given Version.

        :param version:
          Version object.
        :returns:
          Tuple of:
              Boolean indicating whether this Address should get an alert.
              True if (conditions below are combined with AND):
               - Elapsed time since event is less than 8 hours
               - Address has not previously been alerted about this event OR previous 
                 alert level was 2 levels different from current.
               - Event occurred inside at least one of the address' regions of 
                 interest (defaults to True if user has no regions defined).
               - Event meets or exceeds one of the address thresholds (MMI, magnitude, or EIS).
              Boolean indicating whether this address has been notified for the event before.
        """
        levels = ['green','yellow','orange','red']
        

        #get the alert level for the most recently alerted version this user received
        #first get the event id for this version of an event
        eid = version.event_id
        #next find all the versions for this address that also have that event_id
        notified_before = False
        highest_level = -1

        #just get the versions for this event id
        sversions = []
        for sversion in self.versions:
            if sversion.event_id != eid:
                continue
            sversions.append(sversion)
            if sversion.summarylevel > highest_level:
                highest_level = sversion.summarylevel
            notified_before = True
        sversions = sorted(sversions,key=lambda v: v.number)

        #shortcut to True here if notified_before is true and renotify is true
        last_version_pending = False
        if notified_before:
            if sversions[-1].was_pending:
                last_version_pending = True

        #anybody who's been previously notified should be re-notified if that flag is set
        if notified_before and renotify:
            return (True,True)

        #anybody who's been most recently notified of a pending event, should
        #be re-notified if the release flag is set
        if notified_before and last_version_pending and release:
            return (True,True)

        #check the version time against the current time, reject if older than 8 hours
        if not ignore_time_limit:
            if datetime.utcnow() > version.time + timedelta(seconds=MAX_ELAPSED_SECONDS):
                return (False,notified_before)
        
        #shortcut to True here if the most recent version for this event
        #was NOT released (i.e., pending), but only if this version has been released.
        if (len(sversions) and not sversions[-1].released) and version.released:
            return (True,True)
            
        should_alert = False
        for profile in self.profiles:
            if profile.shouldAlert(version,highest_level):
                should_alert = True
                break

        return (should_alert,notified_before)

    def fromDict(self,session,addressdict):
        reqfields = set(['email','is_primary','priority','profiles','format'])
        if reqfields <= set(addressdict.keys()):
            pass
        else:
            missing = list(reqfields - set(addressdict.keys()))
            raise PagerException('Missing required fields for address: %s' % str(missing))
        #set the fields for the address object
        self.email = addressdict['email']
        self.is_primary = addressdict['is_primary']
        self.priority = addressdict['priority']
        self.format = addressdict['format']
        if not len(addressdict['profiles']):
            print('Warning: Address %s has NO profiles in the JSON file. Continuing.' % self.email)
        for profiledict in addressdict['profiles']:
            profile = Profile()
            try:
                profile.fromDict(session,profiledict)
            except PagerException as pe:
                raise PagerException('Error: "%s" when loading profile for address %s.' % (str(pe),self.email))
            if not len(profile.thresholds):
                print('Warning: Address %s has NO thresholds in one of the profiles. Continuing.' % self.email)
            self.profiles.append(profile)

    def toDict(self):
        addressdict = {'email':self.email,
                       'is_primary':self.is_primary,
                       'format':self.format,
                       'priority':self.priority}
        profiles = []
        for profile in self.profiles:
            pdict = profile.toDict()
            profiles.append(pdict)
        addressdict['profiles'] = profiles
        return addressdict

class Profile(Base):
    """Class representing a user's profile.

    Relationship descriptions:
     - A profile belongs to one address.
     - A profile can have many thresholds.
     - A profile can have many regions.
    """
    __tablename__ = 'profile'
    id = Column(Integer, primary_key=True)
    address_id = Column(Integer, ForeignKey('address.id'))

    #A profile can have many regions
    regions = relationship(
        "Region",
        secondary=profile_region_bridge,
        back_populates="profiles")

    #A profile belongs to one address
    address = relationship("Address", back_populates="profiles")

    #A profile can have many thresholds
    thresholds = relationship("Threshold",back_populates="profile")

    def __repr__(self):
        return "<Profile(%i thresholds,%i regions)>" % (len(self.thresholds),len(self.regions))

    def shouldAlert(self,version,highest_level):
        if not len(self.regions) and not len(self.thresholds):
            return False
        #figure out if this point is in a given region
        inside_region = False
        #No regions implies the whole globe
        if not len(self.regions):
            inside_region = True
        else:
            for region in self.regions:
                inside_region = region.containsPoint(version.lat,version.lon)
                if inside_region:
                    break

        #determine if this event crosses any thresholds
        meets_threshold = False
        if not len(self.thresholds):
            meets_threshold = True
        else:
            for threshold in self.thresholds:
                if threshold.isMet(version,highest_level):
                    meets_threshold = True
                    break
        if inside_region and meets_threshold:
            return True

        return False

    def fromDict(self,session,profiledict):
        reqfields = set(['regions','thresholds'])
        if reqfields <= set(profiledict.keys()):
            pass
        else:
            missing = list(reqfields - set(profiledict.keys()))
            raise PagerException('Missing required fields for profile: %s' % str(missing))
        
        for regiondict in profiledict['regions']:
            rgroup,rname = regiondict['name'].split('-')
            region = session.query(Region).filter(Region.name == rname).first()
            if region is None:
                raise PagerException('No region named %s found in the database.' % regiondict['name'])
            self.regions.append(region)
        
        for thresholddict in profiledict['thresholds']:
            threshold = Threshold()
            threshold.fromDict(session,thresholddict)
            self.thresholds.append(threshold)

    def toDict(self):
        profiledict = {}
        regions = []
        for region in self.regions:
            #remember that we're not deflating a Region object, we just want the reference to 
            #it (i.e., its name).
            rgroup = region.regiongroup.groupname
            regiondict = {'name':rgroup + '-' + region.name}
            regions.append(regiondict)
        thresholds = []
        for threshold in self.thresholds:
            thresholddict = threshold.toDict()
            thresholds.append(thresholddict)
        profiledict['regions'] = regions
        profiledict['thresholds'] = thresholds
        return profiledict
        
class Organization(Base):
    """Class representing an organization (USGS, FEMA, etc.)

    Relationship descriptions:
     - An organization can have many users.
    """
    __tablename__ = 'organization'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    shortname = Column(String, nullable=False)

    #An organization can have many users
    users = relationship("User", order_by=User.id, back_populates="organization")
    
    def __repr__(self):
        return "<Organization(name='%s', %i members)>" % (self.name,len(self.users))

    def fromDict(self,session,orgdict):
        reqfields = set(['name','shortname'])
        if reqfields <= set(orgdict.keys()):
            pass
        else:
            missing = list(reqfields - set(orgdict.keys()))
            raise PagerException('Missing required fields for user: %s' % str(missing))
        self.shortname = orgdict['shortname']
        self.name = orgdict['name']
        session.add(self)
        session.commit()

class Event(Base):
    """Class representing an earthquake event.

    Relationship descriptions:
     - An event can have many versions.
    """
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    eventcode = Column(String, nullable=False)

    #An event can have many versions
    versions = relationship("Version", back_populates="event",cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Event(eventcode='%s', %i versions)>" % (self.eventcode,len(self.versions))

class Version(Base):
    """Class representing a version of an earthquake event.

    Relationship descriptions:
     - A version belongs to one event.
     - A version can be linked to many email addresses.
    """
    __tablename__ = 'version'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('event.id',ondelete='CASCADE'),nullable=False)
    versioncode = Column(String, nullable=False)
    time = Column(DateTime, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    magnitude = Column(Float, nullable=False)
    number = Column(Integer, nullable=False)
    country = Column(String, nullable=False) #most impacted country
    fatlevel = Column(Integer, nullable=False)
    ecolevel = Column(Integer, nullable=False)
    summarylevel = Column(Integer, nullable=False)
    processtime = Column(DateTime, nullable=False)
    released = Column(Boolean,nullable=False)
    was_pending = Column(Boolean,nullable=False)
    maxmmi = Column(Float, nullable=False)

    #A user can have many addresses
    event = relationship("Event", back_populates="versions")

    #An version can have many addresses
    addresses = relationship(
        "Address",
        secondary=version_address_bridge,
        back_populates="versions")

    def __repr__(self):
        return "<Version(%s #%i, %s M%.1f)>" % (self.versioncode,self.number,str(self.time),self.magnitude)
    
class AlertScheme(Base):
    """Class representing an alert scheme (Magnitude, MMI, Earthquake Impact Scale, etc.).

    Relationship descriptions:
     - An alert scheme can have many levels.
    """
    __tablename__ = 'alertscheme'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    adesc = Column(String, nullable=False)
    valuetype = Column(String, nullable=False)
    isdiscrete = Column(Boolean, nullable=False)
    minlevel = Column(Float,nullable=True)
    maxlevel = Column(Float,nullable=True)

    #An alertscheme can have many levels
    levels = relationship("Level",back_populates="alertscheme")

    def __repr__(self):
        return "<AlertScheme(name='%s')>" % (self.name)

    def fromDict(self,session,schemedict):
        reqfields = set(['name','adesc','valuetype','isdiscrete','minlevel','maxlevel'])
        if reqfields <= set(schemedict.keys()):
            pass
        else:
            missing = list(reqfields - set(schemedict.keys()))
            raise PagerException('Missing required fields for alert scheme: %s' % str(missing))
        tscheme = AlertScheme(name=schemedict['name'],
                              adesc=schemedict['adesc'],
                              valuetype=schemedict['valuetype'],
                              isdiscrete=schemedict['isdiscrete'],
                              minlevel=schemedict['minlevel'],
                              maxlevel=schemedict['maxlevel'])
        session.add(tscheme)

    def toDict(self):
        schemedict = {'name':self.name,
                      'adesc':self.adesc,
                      'valuetype':self.valuetype,
                      'isdiscrete':self.isdiscrete,
                      'minlevel':self.minlevel,
                      'maxlevel':self.maxlevel}
        return schemedict
    
class Threshold(Base):
    """Class representing an alert threshold (magnitude value, EIS level, etc.)

    Relationship descriptions:
     - A threshold is associated with one alert scheme.
     - A threshold belongs to one profile.
    """
    __tablename__ = 'threshold'
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profile.id'))
    alertscheme_id = Column(Integer, ForeignKey('alertscheme.id'))
    value = Column(String, nullable=False)

    #A threshold can have one alertscheme
    alertscheme = relationship("AlertScheme", uselist=False)

    #A threshold belongs to one profile.
    profile = relationship("Profile", back_populates="thresholds")

    def __repr__(self):
        return "<Threshold(type='%s', value='%s')>" % (self.alertscheme.name,self.value)
    
    def isMet(self,version,highest_level):
        """Determine if input earthquake event version meets or exceeds this threshold.

        :param version:
          Version object, containing magnitude, MMI, and alert level information.
        :param highest_level:
          Highest level of this event for which this Address was previously notified.
        :param alerted_before:
          Boolean indicating whether the profile to which this threshold belongs
          has been notified about this event previously.
        :returns:
          Boolean indicating whether threshold has been met or exceeeded.
        """
        alertdict = {'green':0,
                     'yellow':1,
                     'orange':2,
                     'red':3}
        levels = ['green','yellow','orange','red']
        #This is complicated.  If the user has not been notified about
        #this event before and the current level exceeds the threshold, then they should
        #be notified.  If they haven't been notified and current level is below threshold, then no notification.
        #If the user HAS been notified about this event, then if the current alert level is two or more
        #levels *different* from the 
        if self.alertscheme.name == 'eis':
            threshlevel = alertdict[self.value]
            if highest_level < 0:
                if version.summarylevel >= threshlevel:
                    return True
                else:
                    return False
            else:
                two_levels_different = np.abs(version.summarylevel - highest_level) >= MAX_EIS_LEVELS
                if two_levels_different:
                    return True
                else:
                    return False
        elif self.alertscheme.name == 'mmi':
            thislevel = float(self.value)
            if version.maxmmi >= thislevel and highest_level < 0:
                return True
        else: #self.alertscheme.name == 'mag':
            thislevel = float(self.value)
            if version.magnitude >= thislevel and highest_level < 0:
                return True
        return False

    def fromDict(self,session,thresholddict):
        tvalue = thresholddict['value']
        scheme = session.query(AlertScheme).filter(AlertScheme.name == thresholddict['alertscheme']).first()
        if scheme is None:
            raise PagerException('No alert scheme named %s exists in the database.' % thresholddict['alertscheme'])
        if not scheme.isdiscrete:
            if scheme.valuetype == 'Float':
                tvalue = float(tvalue)
            else:
                tvalue = int(tvalue)
            if tvalue < scheme.minlevel or tvalue > scheme.maxlevel:
                raise PagerException('Threshold for %s is outside range.' % scheme.name)
        self.alertscheme = scheme
        self.value = thresholddict['value']

    def toDict(self):
        thresholddict = {'value':self.value,
                         'alertscheme':self.alertscheme.name}
        return thresholddict

class Level(Base):
    """Class representing an alert threshold (magnitude value, EIS level, etc.)

    """
    __tablename__ = 'level'
    id = Column(Integer, primary_key=True)
    alertscheme_id = Column(Integer, ForeignKey('alertscheme.id'))
    ordernum = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    alertscheme = relationship("AlertScheme", back_populates="levels")
    
    def __repr__(self):
        return "<Level(%s)>" % (self.name)
    
class RegionGroup(Base):
    """Class representing a group of regions (FEMA, US military, OFDA, etc.)

    Relationship descriptions:
     - A region group can have many regions.
    """
    __tablename__ = 'regiongroup'
    id = Column(Integer, primary_key=True)
    groupname = Column(String, nullable=False)

    #A regiongroup can have many regions
    regions = relationship("Region", back_populates="regiongroup")

    def __repr__(self):
        return "<RegionGroup(%s)>" % (self.groupname)

class Region(Base):
    """Class representing a region of interest (US military Northern Command, or NORTHCOM, for example.)

    Relationship descriptions:
     - A region can be associated with many addresses.
    """
    __tablename__ = 'region'
    id = Column(Integer, primary_key=True)
    regiongroup_id = Column(Integer, ForeignKey('regiongroup.id'))
    name = Column(String, nullable=False)
    desc = Column(String, nullable=False)
    poly = Column(LargeBinary, nullable=False)
    xmin = Column(Float, nullable=False)
    xmax = Column(Float, nullable=False)
    ymin = Column(Float, nullable=False)
    ymax = Column(Float, nullable=False)

    #A region can have many profiles
    profiles = relationship("Profile",
                             secondary=profile_region_bridge,
                             back_populates="regions")

    regiongroup = relationship("RegionGroup",back_populates="regions")

    def __repr__(self):
        return "<Region(name=%s, desc=%s)>" % (self.name,self.desc)

    def getPolygon(self):
        polystr = self.poly.decode('utf-8')
        polydict = json.loads(polystr)
        m = shape(GeoThing(polydict))
        return m
    
    def containsPoint(self,lat,lon):
        """Determine whether a given lat/lon is inside the region.

        :param lat:
          Epicentral latitude.
        :param lon:
          Epicentral longitude.
        :returns:
          True if epicenter is inside region, False if not.
        """
        #the polygon is a JSON string encoded to bytes - decode, convert to JSON,
        #project into an orthographic projection,  then turn into shapely object.
        polystr = self.poly.decode('utf-8')
        polydict = json.loads(polystr)
        polygon = shape(polydict)
        if polygon.contains(Point(lon,lat)):
            return True

        return False

    def fromDict(self,session,regiondict):
        reqfields = set(['type','geometry','properties'])
        if reqfields <= set(regiondict.keys()):
            pass
        else:
            missing = list(reqfields - set(regiondict.keys()))
            raise PagerException('Missing required fields for region: %s' % str(missing))
        regioninfo = regiondict['properties']['code']
        rgroupname,regioncode = regioninfo.split('-')
        regiondesc = regiondict['properties']['desc']

        #try to find this region in the database
        regiongroup = session.query(RegionGroup).filter(RegionGroup.groupname == rgroupname).first()
        if regiongroup is None:
            regiongroup = RegionGroup(groupname=rgroupname)
        
        poly = regiondict['geometry']
        polybytes = bytes(json.dumps(poly),'utf-8')
        tshape = shape(poly)
        if not tshape.is_valid:
            x = 1
        xmin,ymin,xmax,ymax = tshape.bounds
        self.name = regioncode
        self.desc = regiondesc
        self.poly = polybytes
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.regiongroup = regiongroup
        session.add(self)
        session.commit()

    def toDict(self):
        polydata = json.loads(self.poly.decode('utf-8'))
        regioncode = self.regiongroup.groupname + '-' + self.name
        regiondict = {'type':'Feature',
                      'geometry':polydata,
                      'properties':{'code':regioncode,
                                    'desc':self.desc}}
        return regiondict
                      
    
def get_session(url='sqlite:///:memory:',create_db=False):
    """Get a SQLAlchemy Session instance for input database URL.

    :param url:
      SQLAlchemy URL for database, described here:
        http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls.
    :param create_db:
      Boolean indicating whether to create database from scratch.  Use with caution.
    :returns:
      Sqlalchemy Session instance.
    """
    #Create a sqlite in-memory database engine
    if not database_exists(url):
        create_database(url)
    else:
        if create_db:
            create_database(url)
            
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)

    #create a session object that we can use to insert and 
    #extract information from the database
    Session = sessionmaker(bind=engine,autoflush=False)
    session = Session()

    return session

def create_db(url,schemadir,users_jsonfile=None,orgs_jsonfile=None):
    session = get_session(url,create_db=True)

    #Create the alertscheme and level tables, fill them in
    magscheme = {'name':'mag','adesc':'Magnitude',
                 'valuetype':'Float','isdiscrete':False,
                 'minlevel':0,'maxlevel':10}
    mmischeme = {'name':'mmi','adesc':'Modified Mercalli Intensity',
                 'valuetype':'Float','isdiscrete':False,
                 'minlevel':0,'maxlevel':10}
    eisscheme = {'name':'eis','adesc':'Earthquake Impact Scale',
                 'valuetype':'String','isdiscrete':True,
                 'minlevel':None,'maxlevel':None}
    schemes = [magscheme,mmischeme,eisscheme]
    eis_id = None
    for scheme in schemes:
        tscheme = AlertScheme(name=scheme['name'],
                              adesc=scheme['adesc'],
                              valuetype=scheme['valuetype'],
                              isdiscrete=scheme['isdiscrete'],
                              minlevel=scheme['minlevel'],
                              maxlevel=scheme['maxlevel'])
        session.add(tscheme)
        session.commit()
        
    eis = session.query(AlertScheme).filter(AlertScheme.name == 'eis').first()
    #Level table
    levels = [{'ordernum':0,'name':'green'},
              {'ordernum':1,'name':'yellow'},
              {'ordernum':2,'name':'orange'},
              {'ordernum':3,'name':'red'}]
    for level in levels:
        tlevel = Level(name=level['name'],
                       ordernum=level['ordernum'])
        tlevel.alertscheme = eis
        session.add(tlevel)
    session.commit()

    #regions - these are pretty well set in stone, therefore in the repository
    regions_jsonfile = os.path.join(schemadir,'regions.json')
    #organizations - this is always changing, so should be user supplied
    #default is just to have a testing set with just USGS
    if orgs_jsonfile is None:
        orgs_jsonfile = os.path.join(schemadir,'shortorgs.json')

    #Load regions - the input file is a dictionary, not a list of regions.
    data = open(regions_jsonfile,'rt').read()
    regions = json.loads(data)
    for regioncode,regiondict in regions.items():
        region = Region()
        region.fromDict(session,regiondict) #this adds to session and commits()
        

    #load whatever organizations we have
    orgs = json.loads(open(orgs_jsonfile,'rt').read())
    for orgdict in orgs:
        org = Organization()
        org.fromDict(session,orgdict) #this adds and commits

    #load the users, if they are specified
    if users_jsonfile is not None:
        users = json.loads(open(users_jsonfile,'rt').read())
        for userdict in users:
            user = User()
            user.fromDict(session,userdict)
    
    return session

def serialize_users(session,jsonfile):
    #Back up the list of users to a JSON file
    users = session.query(User).all()
    userlist = []
    for user in users:
        userdict = user.toDict()
        userlist.append(userdict)
    f = open(jsonfile,'wt')
    json.dump(userlist,f,indent=2)
    f.close()

def get_file_url(dbfile):
    fileurl = 'sqlite:///%s' % dbfile
    return fileurl

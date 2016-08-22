#!/usr/bin/env python

#stdlib imports
from datetime import datetime,timedelta
import enum
import sys
import json
import io
import pickle

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

#link the user and notification_group tables 
user_notification_bridge = Table('user_notification_bridge', Base.metadata,
                                 Column('user_id', Integer, ForeignKey('user.id')),
                                 Column('notification_id', Integer, ForeignKey('notificationgroup.id')))

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
    - A User can belong to many NotificationGroups.
    
    """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    lastname = Column(String)
    firstname = Column(String)
    createdon = Column(DateTime)
    organization_id = Column(Integer, ForeignKey('organization.id'))

    #A User can have many addresses
    addresses = relationship("Address", back_populates="user")

    #A user can belong to many notification groups
    notification_groups = relationship("NotificationGroup",
                                       secondary=user_notification_bridge,
                                       back_populates="users")

    #A user can belong to one organization
    organization = relationship("Organization", back_populates="users")
    
    def __init__(self,lastname,firstname,createdon=None):
        """
        :param lastname:
          User's last name (string).
        :param firstname:
          User's first name (string).
        :param createdon:
          UTC datetime object when user was added to the system.
        """
        self.lastname = lastname
        self.firstname = firstname
        if createdon is None:
            self.createdon = datetime.utcnow()
        else:
            self.createdon = createdon

    def __repr__(self):
        fmt = "<User(id=%i,name='%s %s', created='%s')>"
        tpl = (self.id,self.firstname,self.lastname,str(self.createdon))
        return fmt % tpl

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
    user_id = Column(Integer, ForeignKey('user.id'))
    is_primary = Column(Boolean,nullable=False)
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

    def shouldAlert(self,version):
        """Determine whether an alert should be sent to this address for given Version.

        :param version:
          Version object.
        :returns:
          Boolean indicating whether this Address should get an alert.
          True if (conditions below are combined with AND):
           - Elapsed time since event is less than 8 hours
           - Address has not previously been alerted about this event OR previous 
             alert level was 2 levels different from current.
           - Event occurred inside at least one of the address' regions of 
             interest (defaults to True if user has no regions defined).
           - Event meets or exceeds one of the address thresholds (MMI, magnitude, or EIS).
        """
        #check the version time against the current time, reject if older than 8 hours
        if datetime.utcnow() > version.time + timedelta(seconds=MAX_ELAPSED_SECONDS):
            return False

        #get the alert level for the most recently alerted version this user received
        #first get the event id for this version of an event
        eid = version.event_id
        #next find all the versions for this address that also have that event_id
        notified_before = False
        highest_level = -1
        #newlist = sorted(ut, key=lambda x: x.count, reverse=True)
        sversions = sorted(self.versions,key=lambda v: v.processtime)
        for sversion in sversions:
            if sversion.event_id != eid:
                continue
            notified_before = True
            highest_level = alertdict[sversion.summarylevel]
            
        should_alert = False
        for profile in self.profiles:
            if profile.shouldAlert(version,highest_level):
                should_alert = True
                break

        return should_alert
        

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
        #figure out if this point is in a given region
        inside_region = False
        #No regions implies the whole globe
        if not len(self.regions):
            inside_region = True
        else:
            for region in self.regions:
                inside_region = region.containsEpicenter(version.lat,version.lon)
                if inside_region:
                    break

        #determine if this event crosses any thresholds
        meets_threshold = False
        for threshold in self.thresholds:
            if threshold.isMet(version,highest_level):
                meets_threshold = True
                break
        if inside_region and meets_threshold:
            return True

        return False
        
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

class Event(Base):
    """Class representing an earthquake event.

    Relationship descriptions:
     - An event can have many versions.
    """
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    eventcode = Column(String, nullable=False)

    #An event can have many versions
    versions = relationship("Version", back_populates="event")

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
    event_id = Column(Integer, ForeignKey('event.id'))
    versioncode = Column(String, nullable=False)
    time = Column(DateTime, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    magnitude = Column(Float, nullable=False)
    number = Column(Integer, nullable=False)
    summarylevel = Column(Enum(_AlertEnum), nullable=False)
    processtime = Column(DateTime, nullable=False)
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
    levels = relationship("Level")

    def __repr__(self):
        return "<AlertScheme(name='%s')>" % (self.name)
    
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
        :returns:
          Boolean indicating whether threshold has been met or exceeeded.
        """
        alertdict = {'green':0,
                     'yellow':1,
                     'orange':2,
                     'red':3}
        if self.alertscheme.name == 'eis':
            thislevel = alertdict[version.summarylevel]
            is_higher = np.abs(thislevel - highest_level) > MAX_EIS_LEVELS
            threshlevel = alertdict[self.value]
            if thislevel >= threshlevel and is_higher:
                return True
        elif self.alertscheme.name == 'mmi':
            thislevel = float(self.value)
            if version.maxmmi >= thislevel:
                return True
        else: #self.alertscheme.name == 'mag':
            thislevel = float(self.value)
            if version.magnitude >= thislevel:
                return True
        return False

class Level(Base):
    """Class representing an alert threshold (magnitude value, EIS level, etc.)

    """
    __tablename__ = 'level'
    id = Column(Integer, primary_key=True)
    alertscheme_id = Column(Integer, ForeignKey('alertscheme.id'))
    ordernum = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    def __repr__(self):
        return "<Level(%s)>" % (self.name)

class NotificationGroup(Base):
    """Class representing a notification group (Critical User, PAGER developer, etc.)

    Relationship descriptions:
     - A notification group is associated with many users.
    """
    __tablename__ = 'notificationgroup'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    displaytext = Column(Integer, nullable=False)

    #A NotificationGroup can have many users
    users = relationship("User",
                         secondary=user_notification_bridge,
                         back_populates="notification_groups")

    def __repr__(self):
        return "<NotificationGroup(%s)>" % (self.name)
    
class RegionGroup(Base):
    """Class representing a group of regions (FEMA, US military, OFDA, etc.)

    Relationship descriptions:
     - A region group can have many regions.
    """
    __tablename__ = 'regiongroup'
    id = Column(Integer, primary_key=True)
    groupname = Column(String, nullable=False)

    #A regiongroup can have many regions
    regions = relationship("Region")

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
    poly = Column(LargeBinary, nullable=False)
    xmin = Column(Float, nullable=False)
    xmax = Column(Float, nullable=False)
    ymin = Column(Float, nullable=False)
    ymax = Column(Float, nullable=False)

    #A region can have many profiles
    profiles = relationship("Profile",
                             secondary=profile_region_bridge,
                             back_populates="regions")

    def __repr__(self):
        return "<Region(name=%s)>" % self.name

    def getPolygon(self):
        polystr = self.poly.decode('utf-8')
        polydict = json.loads(polystr)
        m = shape(GeoThing(polydict))
        return m
    
    def containsEpicenter(self,lat,lon):
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
        pcoords = []
        for cblock in polydict['coordinates']:
            plon,plat = zip(*cblock)
            lonmin = min(plon)
            lonmax = max(plon)
            latmin = min(plat)
            latmax = max(plat)
            proj = get_orthographic_projection(lonmin,lonmax,latmax,latmin)
            try:
                x,y = proj(lon,lat)
            except ValueError as ve:
                continue
            try:
                px,py = proj(plon,plat)
            except ValueError as ve:
                x = 1
            pxy = zip(px,py)
            polygon = Polygon(pxy)
            if polygon.contains(Point(x,y)):
                return True

        return False

    
    
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
    Session = sessionmaker(bind=engine)
    session = Session()

    return session
    
def create_db(url,jsonfile,nusers=None,create_db=False):
    """Create a PAGER email database from input JSON file.

    :param url:
      SQLAlchemy URL for database, described here:
        http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls.
    :param jsonfile:
      JSON file containing information about users, addresses, thresholds, events, versions.
      #TODO describe format in detail.
    :param nusers:
      Number of users to sample randomly from input JSON file.  
        None means all users will be inserted into database.
    :param create_db:
      Boolean indicating whether to create database from scratch.  Use with caution.
    :returns:
      Sqlalchemy Session instance.
    """
    session = get_session(url,create_db=create_db)

    #load the anonymized test data set from the repository
    data = open(jsonfile,'rt').read()
    jdict = json.loads(data)
    sys.stderr.write('Loaded the JSON data.\n')
    sys.stderr.flush()

    #add the organizations first
    orgdict = {}
    for org in jdict['orgs']:
        torg = Organization(name=org['name'],shortname=org['shortname'])
        session.add(torg)
        session.commit()
        orgdict[torg.shortname] = torg.id
    sys.stderr.write('Created the organizations.\n')
    sys.stderr.flush()

    #then add the notification groups
    groupdict = {}
    for group in jdict['groups']:
        tgroup = NotificationGroup(name=group['name'],displaytext=group['displaytext'])
        session.add(tgroup)
        session.commit()
        groupdict[tgroup.name] = tgroup.id
    sys.stderr.write('Created the groups.\n')
    sys.stderr.flush()

    #Now add events and versions
    vdict = {} #keys are pre-existing version ids, values are new version ids
    for event in jdict['events']:
        tevent = Event(eventcode=event['eventcode'])
        session.add(tevent)
        session.commit()
        versions = []
        for version in event['versions']:
            tversion = Version(event_id=tevent.id,
                               versioncode=version['versioncode'],
                               time=datetime.strptime(version['time'],TIME_FORMAT),
                               lat=version['lat'],
                               lon=version['lon'],
                               depth=version['depth'],
                               magnitude=version['mag'],
                               number = int(version['number']),
                               maxmmi = version['maxmmi'],
                               processtime = datetime.strptime(version['processtime'],TIME_FORMAT),
                               summarylevel=version['summarylevel'])
            session.add(tversion)
            session.commit()
            vdict[version['id']] = tversion.id
            #tevent.versions.append(tversion)
        session.commit()
    sys.stderr.write('Created the events.\n')
    sys.stderr.flush()

    #Create the alertscheme and level tables, fill them in
    magscheme = {'name':'mag','adesc':'Magnitude',
                 'valuetype':'Float','isdiscrete':False,
                 'minlevel':0,'maxlevel':11}
    mmischeme = {'name':'mmi','adesc':'Modified Mercalli Intensity',
                 'valuetype':'Float','isdiscrete':False,
                 'minlevel':0,'maxlevel':11}
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
        if scheme['name'] == 'eis':
            eis_id = tscheme.id

    #Level table
    levels = [{'alertscheme_id':eis_id,'ordernum':0,'name':'green'},
              {'alertscheme_id':eis_id,'ordernum':1,'name':'yellow'},
              {'alertscheme_id':eis_id,'ordernum':2,'name':'orange'},
              {'alertscheme_id':eis_id,'ordernum':3,'name':'red'}]
    for level in levels:
        tlevel = Level(name=level['name'],
                                   ordernum=level['ordernum'],
                                   alertscheme_id=eis_id)
        session.add(tlevel)
    session.commit()
    sys.stderr.write('Created the alert schemes and levels.\n')
    sys.stderr.flush()

    #Create regions and regiongroups
    region_group_dict = {}
    for regioncode,region in jdict['regions'].items():
        rgroupname,rcode = regioncode.split('-')
        if rgroupname not in region_group_dict:
            trgroup = RegionGroup(groupname=rgroupname)
            session.add(trgroup)
            region_group_dict[rgroupname] = trgroup
        else:
            trgroup = region_group_dict[rgroupname]
        poly = region['geometry']
        polybytes = bytes(json.dumps(poly),'utf-8')
        xmin = 99999999
        xmax = -99999999
        ymin = xmin
        ymax = xmax
        for cblock in poly['coordinates']:
            x,y = zip(*cblock)
            if min(x) < xmin:
                xmin = min(x)
            if max(x) > xmax:
                xmax = max(x)
            if min(y) < ymin:
                ymin = min(y)
            if max(y) > ymax:
                ymax = max(y)    
        tregion = Region(name=rcode,poly=polybytes,xmin=xmin,xmax=xmax,ymin=ymin,ymax=ymax)
        trgroup.regions.append(tregion)
    session.commit()
    sys.stderr.write('Created the regions and region groups.\n')
    sys.stderr.flush()

    #Get the data that links versions to addresses
    versionid,addressid = zip(*jdict['version_address'])
    versionid = np.array(versionid)
    addressid = np.array(addressid)
    
    #Now start adding users, addresses, etc.
    adict = {} #old address id => new address id
    allidx = np.arange(0,len(jdict['users']))
    if nusers is None:
        usamples = allidx
    else:
        usamples = np.random.choice(allidx,size=nusers,replace=False)
        
    for isample in usamples:
        user = jdict['users'][isample]
        tcreated = datetime.strptime(user['createdon'],TIME_FORMAT)
        tuser = User(user['lastname'],user['firstname'],createdon=tcreated)

        orgshortname = user['org']
        torg = session.query(Organization).filter(Organization.shortname==orgshortname).first()
        tuser.organization = torg
        
        for address in user['emails']:
            taddress = Address(email=address['email'],
                               is_primary=address['isprimary'],
                               priority=address['priority'],
                               format='unknown')

            #Get the list of versions that were associated with this address...
            oldaddressid = address['id']
            addressidx = np.where(addressid == oldaddressid)[0]
            for idx in addressidx:
                oldversionid = versionid[idx]
                newversionid = vdict[oldversionid]
                version = session.query(Version).filter(Version.id==newversionid).first()
                taddress.versions.append(version)
                
            for profile in address['profiles']:
                #We used to have a format table which theoretically allowed each address to have
                #many email formats.  We never allowed this in practice, so we're just attaching the format
                #string to the address table
                #three formats: short, long, pdf
                if profile['format'].find('pdf') > 0:
                    taddress.format = 'pdf'
                elif profile['format'].find('short') > 0:
                    taddress.format = 'short'
                else:
                    taddress.format = 'long'

                tprofile = Profile()

                for regioncode in profile['regioncodes']:
                    rgroup,rcode = regioncode.split('-')
                    tregion = session.query(Region).filter(Region.name==rcode).first()
                    tprofile.regions.append(tregion)

                for threshold in profile['thresholds']:
                    thing = session.query(AlertScheme).filter(AlertScheme.name == threshold['scheme']).first()
                    scheme_id = thing.id
                    value = threshold['threshold']
                    t_threshold = Threshold(alertscheme_id=scheme_id,
                                            value=value)
                    tprofile.thresholds.append(t_threshold)
                taddress.profiles.append(tprofile)

            tuser.addresses.append(taddress)
        session.add(tuser)
    session.commit()
    sys.stderr.write('Created the users, addresses, and profiles.\n')
    sys.stderr.flush()

    session.commit()
    return session

def get_file_url(dbfile):
    fileurl = 'sqlite:///%s' % dbfile
    return fileurl

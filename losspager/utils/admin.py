#stdlib imports
import os.path
import datetime
import zipfile
import glob
import re
import shutil

#local imports
from losspager.utils.exception import PagerException
from losspager.utils.config import read_config,write_config
from losspager.io.pagerdata import PagerData

#third-party imports
from impactutils.comcat.query import ComCatInfo

DATETIMEFMT = '%Y%m%d%H%M%S'


class PagerAdmin(object):
    def __init__(self,pager_folder,archive_folder):
        if not os.path.isdir(pager_folder):
            raise PagerException('PAGER data output folder %s does not exist.' % pager_folder)
        self._pager_folder = pager_folder
        if not os.path.isdir(archive_folder):
            os.makedirs(archive_folder)
        self._archive_folder = archive_folder

    def createEventFolder(self,eventid,event_time):
        eventfolder = os.path.join(self._pager_folder,eventid+'_'+event_time.strftime(DATETIMEFMT))
        #look for folder with that event id in the pager_folder
        teventfolder = self.getEventFolder(eventid)
        if teventfolder is not None:
            return teventfolder
        else:
            try:
                ccinfo = ComCatInfo(eventid)
                #try to get all the possible event ids before failing
                authid,allids = ccinfo.getAssociatedIds()
                allids.append(authid)
                for eid in allids:
                    eventfolder = os.path.join(outfolder,eid+event_time.strftime(DATETIMEFMT))
                    if os.path.isdir(eventfolder):
                        return eventfolder
            except:
                pass
        if not os.path.isdir(eventfolder):
            os.makedirs(eventfolder)
        return eventfolder

    def getEventFolder(self,eventid):
        eventfolders = glob.glob(os.path.join(self._pager_folder,'*%s*' % eventid))
        if len(eventfolders):
            return eventfolders[0]
        return None
        
    def archiveEvent(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        if eventfolder is None:
            return False
        zipname = os.path.join(self._archive_folder,eventid+'.zip')
        myzip = zipfile.ZipFile(zipname,mode='w',compression=zipfile.ZIP_DEFLATED)
        for root,dirs,files in os.walk(eventfolder):
            arcfolder = root[root.find(eventid):]
            for fname in files:
                arcfile = os.path.join(arcfolder,fname)
                fullfile = os.path.join(root,fname)
                myzip.write(fullfile,arcfile)

        myzip.close()
        shutil.rmtree(eventfolder)
        return True

    def getAllEventFolders(self):
        allevents = os.listdir(self._pager_folder)
        event_folders = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            if os.path.isfile(os.path.join(event_folder,'json','event.json')):
                event_folders.append(event_folder)
        return event_folders

    def getAllEvents(self):
        allevents = os.listdir(self._pager_folder)
        events = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            if os.path.isfile(os.path.join(event_folder,'json','event.json')):
                eventid,etime = event.split('_')
                events.append(eventid)
        return events
    
    def archive(self,events=[],all_events=False,events_before=None):
        if all_events ==True and events_before is not None:
            raise PagerException('You cannot choose to archive all events and some events based on time.')
        narchived = 0
        nerrors = 0
        if all_events:
            events = self.getAllEvents()
            for eventid in events:
                result = self.archiveEvent(eventid)
                if result:
                    narchived += 1
                else:
                    narchived += 1
        else:
            for eventid in events:
                eventfolder = self.getEventFolder(eventid)
                if events_before is not None:
                    t,etimestr = eventfolder.split('_')
                    etime = datetime.datetime.strptime(etimestr,DATETIMEFMT)
                    if etime < events_before:
                        self.archiveEvent(eventid)
                    else:
                        continue
                else:
                    self.archiveEvent(eventid)
                
        return (narchived,nerrors)

    def restoreEvent(self,archive_file):
        myzip = zipfile.ZipFile(archive_file,'r')
        fpath,fname = os.path.split(archive_file)
        eventf,ext = os.path.splitext(fpath)
        event_folder = os.path.join(self._pager_folder,eventf)
        if os.path.isdir(event_folder):
            # fmt = 'Event %s could not be restored because there is an event by the same name in the output!'
            # raise PagerException(fmt % fname)
            return False
        myzip.extractall(path=self._pager_folder)
        myzip.close()
        os.remove(archive_file)
        return True
    
    def restore(self,events=[],all=False):
        nrestored = 0
        if all:
            zipfiles = glob.glob(os.path.join(self._pager_archive,'*.zip'))
            for zipfile in zipfiles:
                result = self.restoreEvent(archived_events[0])
                nrestored += result
        else:
            for event in events:
                archived_events = glob.glob(os.path.join(self._archive_folder,'%s_*.zip'))
                if len(archived_events):
                    result = self.restoreEvent(archived_events[0])
                    nrestored += result
        return nrestored

    def stop(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if os.path.isfile(stopfile):
            return (False,eventfolder)
        else:
            f = open(stopfile,'wt')
            f.write('Stopped: %s UTC' % datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            f.close()
        return (True,eventfolder)

    def unstop(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if not os.path.isfile(stopfile):
            return (False,eventfolder)
        else:
            os.remove(stopfile)
        return (True,eventfolder)

    def isStopped(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if not os.path.isfile(stopfile):
            return False
        return True

    def setStatus(self,status='secondary'):
        config = read_config()
        config_file = get_config_file()
        if 'status' not in config:
            lines = open(config_file,'rt').readlines()
            lines.append('status : %s\n' % status)
        else:
            f = open(config_file,'wt')
            for line in lines:
                parts = line.split(':')
                if parts[0].strip() == 'status':
                    line = 'status : %s\n' % status
                else:
                    pass
                f.write(line)
            f.close()
        return True

    def getStatus(self):
        config = read_config()
        status = 'secondary'
        if 'status' in config and config['status'] == 'primary':
            return 'primary'
        return status
        
    
    def query(self,start_time=None,end_time=None,mag_threshold=None,alert_threshold=None,version='last'):
        if start_time is not None:
            if not isinstance(start_time,datetime.datetime):
                raise PagerException('start_time must be a datetime object.')
        if end_time is not None:
            if not isinstance(end_time,datetime.datetime):
                raise PagerException('end_time must be a datetime object.')
            
        all_event_folders = self.getAllEventFolders()
        for event_folder in all_event_folders:
            fpath,efolder = os.path.split(event_folder)
            eventid,etimestr = efolder.split('_')
            etime = datetime.datetime.strptime(etimestr,DATETIMEFMT)
            if start_time is not None:
                if etime < start_time:
                    continue
            if end_time is not None:
                if etime > end_time:
                    continue
            versions = self.getVersions(eventfolder,version=version)

    def getVersionFolders(self,eventfolder):
        contents = os.listdir(eventfolder)
        version_folders = []
        for content in contents:
            if content.startswith('version'):
                version_folders.append(int(re.search('\d+',content)))
        
        return versions
            
    def getVersions(self,eventfolder,version='last'):
        """Return designated version data for given event.

        """
        eventfolder = self.getEventFolder(eventid)
        version_folders = self.getVersionFolders(eventfolder)
        for version_folder in version_folders:
            vdata = self.getVersionData(eventfolder,vnum)
        
    def getVersionData(self,eventfolder,vnum):
        vpath = os.path.join(eventfolder,'version%00i' % vnum)
        jsonfolder = os.path.join(vpath,'json')
        if not os.path.isdir(jsonfolder):
            raise PagerException('Could not find JSON data for version %i' % vnum)
        pdata = PagerData()
        pdata.loadFromJSON(jsonfolder)
        return pdata
            

        

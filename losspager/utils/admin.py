#stdlib imports
import os.path
import datetime
import zipfile
import glob
import re
import shutil
import json
import getpass
from distutils.spawn import find_executable

#local imports
from losspager.utils.exception import PagerException
from losspager.utils.config import read_config,write_config
from losspager.utils.config import get_config_file,get_mail_config_file,read_mail_config
from losspager.io.pagerdata import PagerData

#third-party imports
from impactutils.comcat.query import ComCatInfo
from impactutils.io.cmd import get_command_output
from impactutils.transfer.factory import get_sender_class
import pandas as pd

DATETIMEFMT = '%Y%m%d%H%M%S'
EIGHT_HOURS = 8 * 3600
ALLOWED_ACTIONS = ['release','switch-status','cancel','renotify','stop','unstop','tsunami']
SHAKEMAP_SOURCES = ['us','ci','nc','nn','hv','uw','nn','uu','ak']

def unset_pending(version_folder):
    eventfile = os.path.join(version_folder,'json','event.json')
    f = open(eventfile,'rt')
    jdict = json.load(f)
    f.close()
    if jdict['pager']['alert_level'] == jdict['pager']['true_alert_level']:
        return False
    jdict['pager']['alert_level'] = jdict['pager']['true_alert_level']
    f = open(eventfile,'wt')
    json.dump(jdict,f)
    f.close()
    return True
    
def get_id_and_source(version_folder):
    eventfile = os.path.join(version_folder,'json','event.json')
    f = open(eventfile,'rt')
    jdict = json.load(f)
    f.close()
    eventid = jdict['event']['eventid']
    source = jdict['shakemap']['shake_source']
    return (eventid,source)

def transfer(config,pagerdata,authid,authsource,version_folder,
                 renotify=False,release=False,force_email=False):
    #If system status is primary and transfer options are configured, transfer the output
    #directories using those options
    res = False
    msg = ''
    if 'status' in config and config['status'] == 'primary':
        if 'transfer' in config:
            if 'methods' in config['transfer']:
                print('Running transfer.')
                for method in config['transfer']['methods']:
                    if method not in config['transfer']:
                        sys.stderr.write('Method %s requested but not configured...Skipping.' % method)
                        continue
                    params = config['transfer'][method]
                    if 'remote_directory' in params:
                        vpath,vfolder = os.path.split(version_folder)
                        #append the event id and version folder to our pre-specified output directory
                        params['remote_directory'] = os.path.join(params['remote_directory'],authid,vfolder)
                    params['code'] = authid
                    params['eventsource'] = authsource
                    params['eventsourcecode'] = authid.replace(authsource,'')
                    params['magnitude'] = pagerdata.magnitude
                    params['latitude'] = pagerdata.latitude
                    params['longitude'] = pagerdata.longitude
                    params['depth'] = pagerdata.depth
                    params['eventtime'] = pagerdata.time
                    product_params = {'maxmmi':pagerdata.maxmmi,
                                      'alertlevel':pagerdata.summary_alert_pending}

                    if renotify:
                        product_params['renotify'] = 'true'
                    if release:
                        product_params['release'] = 'true'
                    if force_email:
                        product_params['force-email'] = 'true'
                    sender_class = get_sender_class(method)
                    try:
                        if method == 'pdl':
                            sender = sender_class(properties=params,local_directory=version_folder,
                                                  product_properties=product_params)
                        else:
                            sender = sender_class(properties=params,local_directory=version_folder)
                        try:
                            nfiles,msg = sender.send()
                            res = True
                        except Exception as e:
                            msg = str(e)
                            res = False
                    except Exception as e:
                        msg = str(e)
                        res = False
                        continue
    return (res,msg)

def split_event(eventid):
    event_source = None
    event_source_code = None
    for network in SHAKEMAP_SOURCES:
        if eventid.startswith(network):
            event_source = network
            event_source_code = eventid.replace(network,'')
    if event_source is None:
        event_source = eventid[0:2]
        event_source_code = eventid[2:]
    return (event_source,event_source_code)
            
class RemoteAdmin(object):
    _pdlcmd_pieces = ['[JAVA] -jar [JARFILE] --send --status=UPDATE',
                      '--source=us --type=pager-admin --code=[CODE]',
                      '--property-action=[ACTION]',
                      '--property-action=[EVENTSOURCE]',
                      '--property-action=[EVENTSOURCECODE]',
                      '--property-user=[USER]',
                      '--property-action-time=[ACTION-TIME]',
                      '--privateKey=[PRIVATEKEY]  --configFile=[CONFIGFILE]']
    _pdlcmd = ' '.join(_pdlcmd_pieces)

    _required_init = ['java','jarfile','privatekey','configfile']
    
    _date_time_fmt = '%Y-%m-%dT%H:%M:%S'
    def __init__(self,init_params):
        if not set(self._required_init) <= set(init_params):
            fmt = 'Missing at least one of the required parameters: %s'
            raise Exception(fmt % str(self._required_init))
        self._init_params = init_params

    def sendAction(self,action,eventid):
        if action not in ALLOWED_ACTIONS:
            fmt = 'Action "%s" not in list of allowed actions: "%s"'
            raise Exception(fmt % (action,str(ALLOWED_ACTIONS)))

        pdl_cmd = self._pdlcmd.replace('[JAVA]',self._init_params['java'])
        pdl_cmd = pdl_cmd.replace('[JARFILE]',self._init_params['jarfile'])
        pdl_cmd = pdl_cmd.replace('[privatekey]',self._init_params['privatekey'])
        pdl_cmd = pdl_cmd.replace('[configfile]',self._init_params['configfile'])
        pdl_cmd = pdl_cmd.replace('[CODE]',eventid)
        source,source_code = split_event(eventid)
        pdl_cmd = pdl_cmd.replace('[EVENTSOURCE]',source)
        pdl_cmd = pdl_cmd.replace('[EVENTSOURCECODE]',source_code)
        user = getpass.getuser()
        action_time = datetime.datetime.utcnow().strftime(self._date_time_fmt)
        pdl_cmd = pdl_cmd.replace('[ACTION]',action)
        pdl_cmd = pdl_cmd.replace('[USER]',user)
        pdl_cmd = pdl_cmd.replace('[ACTION-TIME]',action_time)
        res,stdout,stderr = get_command_output(pdl_cmd)
        return (res,stdout,stderr)


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
                    #here we need to look for the *folder* containing the *pattern* with
                    #the eid in question. getEventFolder does this for us.
                    teventfolder = self.getEventFolder(eid)
                    if teventfolder is not None:
                        eventfolder = teventfolder
                        break
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
        fpath,eventname = os.path.split(eventfolder)
        if eventfolder is None:
            return False
        zipname = os.path.join(self._archive_folder,eventname+'.zip')
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
        all_events = os.listdir(self._pager_folder)
        event_folders = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            jsonfile = os.path.join(event_folder,'version.001' ,'json','event.json')
            if os.path.isfile(jsonfile):
                event_folders.append(event_folder)
        return event_folders

    def getAllEvents(self):
        all_events = os.listdir(self._pager_folder)
        events = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            if os.path.isdir(event_folder):
                if event.find('_') > -1:
                    parts = event.split('_')
                    etime = parts[-1]
                    eventid = '_'.join(parts[0:-1])
                else:
                    eventid = event
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
                    nerrors += 1
        else:
            for eventid in events:
                eventfolder = self.getEventFolder(eventid)
                if events_before is not None:
                    t,etimestr = eventfolder.split('_')
                    etime = datetime.datetime.strptime(etimestr,DATETIMEFMT)
                    if etime < events_before:
                        result = self.archiveEvent(eventid)
                        if result:
                            narchived += 1
                        else:
                            nerrors += 1
                    else:
                        continue
                else:
                    result = self.archiveEvent(eventid)
                    if result:
                        narchived += 1
                    else:
                        nerrors += 1
                
        return (narchived,nerrors)

    def restoreEvent(self,archive_file):
        myzip = zipfile.ZipFile(archive_file,'r')
        fpath,fname = os.path.split(archive_file)
        eventf,ext = os.path.splitext(fname)
        event_folder = os.path.join(self._pager_folder,eventf)
        if os.path.isdir(event_folder):
            # fmt = 'Event %s could not be restored because there is an event by the same name in the output!'
            # raise PagerException(fmt % fname)
            return False
        myzip.extractall(path=self._pager_folder)
        myzip.close()
        os.remove(archive_file)
        return True
    
    def restore(self,events=[],all_events=False):
        nrestored = 0
        if all_events:
            zipfiles = glob.glob(os.path.join(self._archive_folder,'*.zip'))
            for zipfile in zipfiles:
                result = self.restoreEvent(zipfile)
                nrestored += result
        else:
            for event in events:
                archived_events = glob.glob(os.path.join(self._archive_folder,'%s_*.zip' % event))
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

    def getMailStatus(self):
        config = read_mail_config()
        status = 'secondary'
        if 'status' in config and config['status'] == 'primary':
            return 'primary'
        return status
    
    def setMailStatus(self,status='secondary'):
        config = read_config()
        config_file = get_mail_config_file()
        lines = open(config_file,'rt').readlines()
        if 'status' not in config:
            lines.append('status : %s\n' % status)
        else:
            newlines = []
            for line in lines:
                parts = line.split(':')
                if parts[0].strip() == 'status':
                    line = 'status : %s\n' % status
                else:
                    pass
                newlines.append(line)
        f = open(config_file,'wt')
        f.writelines(newlines)
        return status
    
    def setStatus(self,status='secondary'):
        config = read_config()
        config_file = get_config_file()
        lines = open(config_file,'rt').readlines()
        if 'status' not in config:
            lines.append('status : %s\n' % status)
        else:
            newlines = []
            for line in lines:
                parts = line.split(':')
                if parts[0].strip() == 'status':
                    line = 'status : %s\n' % status
                else:
                    pass
                newlines.append(line)
        f = open(config_file,'wt')
        f.writelines(newlines)
        return status

    def getStatus(self):
        config = read_config()
        status = 'secondary'
        if 'status' in config and config['status'] == 'primary':
            return 'primary'
        return status

    def getLastVersion(self,event_folder):
        version_folders = glob.glob(os.path.join(event_folder,'version.*'))
        version_folders.sort()
        return version_folders[-1]
    
    def getVersionNumbers(self,event_folder):
        version_folders = glob.glob(os.path.join(event_folder,'version.*'))
        vnums = []
        for vfolder in version_folders:
            fpath,vf = os.path.split(vfolder)
            vnum = int(re.search('\d+',vf).group())
            vnums.append(vnum)

        vnums.sort()
        return vnums

    def toggleTsunami(self,eventid,tsunami='off'):
        toggle = {'on':1,'off':0}
        event_folder = self.getEventFolder(eventid)
        tsunami_file = os.path.join(event_folder,'tsunami')
        f = open(tsunami_file,'wt')
        f.write('%s' % tsunami)
        f.close()
        
        version_folder = sorted(glob.glob(os.path.join(event_folder,'version.*')))[-1]
        res,stdout,stderr = self.runPager(version_folder,tsunami=tsunami)
        return (res,stdout,stderr)

    def runPager(self,versionfolder,release=False,cancel=False,tsunami='auto'):
        gridfile = os.path.join(versionfolder,'grid.xml')
        pagerbin = find_executable('pager')
        if pagerbin is None:
            raise PagerException('Could not find PAGER executable on this system.')
        pagercmd = pagerbin + ' %s' % gridfile
        if release:
            pagercmd += ' --release'
        if cancel:
            pagercmd += ' --cancel'
        pagercmd += ' --tsunami=%s' % tsunami
        res,stdout,stderr = get_command_output(pagercmd)
        return (res,stdout,stderr)
    
    def query(self,start_time=datetime.datetime(1800,1,1),end_time=datetime.datetime.utcnow(),
              mag_threshold=0.0,alert_threshold='green',version='last',eventid=None):
        levels = {'green':0,
                  'yellow':1,
                  'orange':2,
                  'red':3}
        if eventid is not None:
            all_event_folders = [self.getEventFolder(eventid)]
            version = 'all'
        else:
            all_event_folders = self.getAllEventFolders()
        event_data = []
        do_process_time = False
        if eventid is not None:
            do_process_time = True
        
        df = pd.DataFrame(columns=PagerData.getSeriesColumns(processtime=do_process_time))
        jsonfolders = []
        for event_folder in all_event_folders:
            vnums = self.getVersionNumbers(event_folder)
            if version == 'first':
                vnum = vnums[0]
                jsonfolders.append(os.path.join(event_folder,'version.%03d' % vnum,'json'))
            elif version == 'last':
                vnum = vnums[-1]
                jsonfolders.append(os.path.join(event_folder,'version.%03d' % vnum,'json'))
            elif version == 'eight':
                for vnum in vnums:
                    jsonfolder = os.path.join(event_folder,'version.%03d' % vnum,'json')
                    pdata = PagerData()
                    try:
                        pdata.loadFromJSON(jsonfolder)
                    except:
                        continue
                    if pdata.processing_time >= pdata.time + datetime.timedelta(seconds=EIGHT_HOURS):
                        break
                    jsonfolders.append(jsonfolder)
            elif version == 'all':
                for vnum in vnums:
                    jsonfolder = os.path.join(event_folder,'version.%03d' % vnum,'json')
                    jsonfolders.append(jsonfolder)
            else:
                raise PagerException('version option "%s" not supported.' % version)

        broken = []
        for jsonfolder in jsonfolders:
            pdata = PagerData()
            vnum = 1000
            while vnum > 1:
                try:
                    pdata.loadFromJSON(jsonfolder)
                    vnum = 0
                except:
                    #handle the case where the most recent version of the event has some 
                    #sort of error causing it to miss
                    root,jsonfolder = os.path.split(jsonfolder)
                    root2,vfolder = os.path.split(root)
                    vt,vnums = vfolder.split('.')
                    vnum = int(vnums) - 1
                    jsonfolder = os.path.join(root2,'%s.%03d' % (vt,vnum),'json')
                
            if not pdata._is_validated:
                broken.append(jsonfolder)
            meetsLevel = levels[pdata.summary_alert] >= levels[alert_threshold]
            meetsMag = pdata.magnitude >= mag_threshold
            if pdata.time >= start_time and pdata.time <= end_time and meetsLevel and meetsMag:
                row = pdata.toSeries(processtime=do_process_time)
                df = df.append(row,ignore_index=True)
        df.Version = df.Version.astype(int)
        df.Elapsed = df.Elapsed.astype(int)
        df = df.sort_values('EventTime')
        df = df.set_index('EventID')
        return (df,broken)
        
    


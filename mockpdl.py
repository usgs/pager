#!/usr/bin/env python

# stdlib imports
import argparse
import os.path
import json
from collections import OrderedDict

# local imports
from losspager.utils.config import read_config, read_mail_config, write_config, get_mail_config_file
from losspager.io.pagerdata import PagerData
from losspager.utils.admin import PagerAdmin, RemoteAdmin, transfer, unset_pending, get_id_and_source
from losspager.utils.exception import PagerException

# third party
from impactutils.io.cmd import get_command_output

TIMEFMT = '%Y-%m-%dT%H:%M:%S.%f'

def main(args):
    # read global config file
    config = read_config()
    
    # figure out where the output data goes
    pager_folder = config['output_folder']

    # figure out where the archive folder is
    archive_folder = config['archive_folder']
    
    admin = PagerAdmin(pager_folder, archive_folder)
    event_folder = admin.getEventFolder(args.eventid)
    vnumbers = admin.getVersionNumbers(event_folder)
    version_folder = os.path.join(event_folder,'version.%03i' % vnumbers[-1])
    json_folder = os.path.join(version_folder,'json')
    eventfile = os.path.join(json_folder,'event.json')
    eventdict = json.load(open(eventfile,'rt'))

    arguments = OrderedDict()
    arguments['eventid'] = args.eventid
    arguments['directory'] = event_folder
    arguments['type'] = 'losspager'
    if eventdict['shakemap']['shake_type'] == 'SCENARIO':
        arguments['type'] = 'losspager-scenario'
    eventid = eventdict['shakemap']['shake_id']
    source = eventdict['shakemap']['shake_source']
    code = eventid.replace(source,'')
    arguments['code'] = code
    arguments['source'] = source
    arguments['status'] = 'ACTION'
    arguments['action'] = 'UPDATE'
    arguments['preferred-latitude'] = '%.4f' % eventdict['event']['lat']
    arguments['preferred-longitude'] = '%.4f' % eventdict['event']['lon']
    arguments['preferred-depth'] = '%.1f' % eventdict['event']['depth']
    arguments['preferred-magnitude'] = '%.1f' % eventdict['event']['mag']
    etimestr = eventdict['event']['time'].replace(' ','T')+'.000Z'
    arguments['preferred-eventtime'] = etimestr
    argstr = ' '.join(['--'+key+'='+value for key,value in arguments.items()])
    cmd = 'emailpager %s' % argstr
    print(cmd)
    if args.run:
        print('Calling emailpager: "%s"'  % cmd)
        res,stdout,stderr = get_command_output(cmd)
        if res:
            print('Successful.')
        else:
            print('Failure - "%s".' % stderr)
        
if __name__ == '__main__':
    desc = '''Mock PDL making command line call to emailpager, given event ID on the system.
'''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('eventid', help='the id of the event to pass to emailpager')
    parser.add_argument("--run", action='store_true', default=False,
                           help='Actually call emailpager.')
    pargs = parser.parse_args()

    main(pargs)

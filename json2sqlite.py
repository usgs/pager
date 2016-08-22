#!/usr/bin/env python

import os.path
from losspager.schema import emailschema
import sys
import argparse

if __name__ == '__main__':
    desc = 'Export PAGER users, regions, events, etc. from JSON file into Sqlite database.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('jsonfile', help='Specify input JSON file name')
    parser.add_argument('dbfile', help='Specify output sqlite DB file name')
    parser.add_argument('-n','--num-users', type=int,default=None,
                        help='Specify number of users to export')

    args = parser.parse_args()

    tmpfile = 'anonymized_pager_users.db'
    fileurl = 'sqlite:///%s' % args.dbfile
    jsonfile = 'pager_profiles.json'
    session = emailschema.create_db(fileurl,args.jsonfile,nusers=args.num_users,create_db=True)
    nusers = session.query(emailschema.User).count()
    print('There are %i users in this new database.' % nusers)
    session.close()

    #do a quick test of the new database that we created...
    session = emailschema.get_session(fileurl)
    nusers = session.query(emailschema.User).count()
    print('There are %i users in this new database.' % nusers)
    sys.exit(0)



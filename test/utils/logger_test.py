#!/usr/bin/env python

#stdlib imports
import tempfile
import os.path
import sys
import shutil

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#local imports
from losspager.utils.logger import PagerLogger

def test(email=None,host=None):
    tdir = tempfile.mkdtemp()
    try:
        logfile = os.path.join(tdir,'logfile.log')
        print('Logfile will be %s' % logfile)

        redirect = True
        if email is not None:
            redirect = False

        plog = PagerLogger(logfile,from_address=email,mail_host=host,redirect=redirect)
        plogger = plog.getLogger()

        if not redirect:
            plog.addEmailHandler([email])

        if redirect:
            print('This should show up as information! (print function)')
            sys.stderr.write('This should show up as an error! (write method)')
        else:
            plogger.info('This should show up as information! (info method)')
            plogger.error('This should show up as an error! (error method)')
        try:
            raise Exception("This should show up as critical (and perhaps generate an email)!")
        except Exception as e:
            plogger.critical(e)

        plog.stopLogging()
        f = open(logfile,'rt')
        data = f.read()
        print(data)
        assert len(data)
    except Exception as e1:
        pass
    finally:
        shutil.rmtree(tdir)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        email = sys.argv[1]
        host = sys.argv[2]
    else:
        email = None
        host = None
    test(email=email,host=host)

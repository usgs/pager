#!/usr/bin/env python

# stdlib imports
import tempfile
import os.path
import sys
import shutil

# local imports
from losspager.utils.logger import PagerLogger

# this test is disabled for the purposes of pytest
# because if this runs before any other test code
# that calls any code that does logging,
# that code will be looking for the logger
# that we set up here. According to one mailing
# list entry, loggers persist until the shell is closed.


def _test(email=None, host=None):
    tdir = tempfile.mkdtemp()
    try:
        global_log = os.path.join(tdir, 'global.log')

        plog = PagerLogger(global_log, email, email,
                           host, debug=False)
        logger = plog.getLogger()
        logger.info('Test 1')

        version_log = os.path.join(tdir, 'version.log')
        plog.setVersionHandler(version_log)

        logger.info('Test 2')

        if email is not None:
            logger.critical('Help me!')

        for handler in logger.handlers:
            handler.close()

        with open(global_log, 'rt') as f:
            global_text = f.read()

        with open(version_log, 'rt') as f:
            version_text = f.read()

        assert global_text.find('Test 1') > -1
        assert version_text.find('Test 2') > -1

        plog.close()

    except Exception:
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
    _test(email=email, host=host)

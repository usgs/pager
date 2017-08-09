#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir, '..', '..'))
sys.path.insert(0, pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np

#local imports
from losspager.utils import compass

def test():
    print('Testing various different compass angles...')
    assert compass.get_compass_dir(0, 0, 1, 0, format='short') == 'N'
    assert compass.get_compass_dir(0, 0, 0, 1, format='short') == 'E'
    assert compass.get_compass_dir(0, 1, 0, 0, format='short') == 'W'
    assert compass.get_compass_dir(0, 0, -1, 0, format='short') == 'S'

    assert compass.get_compass_dir(0, 0, 1, 1, format='short') == 'NE'
    assert compass.get_compass_dir(0, 0, 1, -1, format='short') == 'NW'
    assert compass.get_compass_dir(0, 0, -1, -1, format='short') == 'SW'
    assert compass.get_compass_dir(0, 0, -1, 1, format='short') == 'SE'
    print('Passed.')

if __name__ == '__main__':
    test()

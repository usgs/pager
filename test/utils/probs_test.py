#!/usr/bin/env python

# stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

# hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
pagerdir = os.path.abspath(os.path.join(homedir, '..', '..'))
sys.path.insert(0, pagerdir)  # put this at the front of the system path, ignoring any installed shakemap stuff

# third party imports 
import numpy as np

# local imports
from losspager.utils.probs import *


def test():
    print('Testing all probs functions...')
    assert phi(5.0) == 0.99999971334842808
    assert invphi(0.99999971334842808) == 4.9999999999701759
    assert calcEmpiricalProbFromValue(2.5, 1e6, 10e6) == 0.82148367161911606
    assert calcEmpiricalValueFromProb(2.5, 1e6, 0.82148367161911606) == 10000000.00000999
    assert calcEmpiricalProbFromRange(2.5, 1e6, [0, 1]) == 1.6362032828176688e-08
    print('Passed testing all probs functions.')

if __name__ == '__main__':
    test()

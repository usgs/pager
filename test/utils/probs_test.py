#!/usr/bin/env python

# stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

# third party imports
import numpy as np

# local imports
from losspager.utils.probs import *


def test():
    print('Testing all probs functions...')
    assert phi(5.0) == 0.99999971334842808
    assert invphi(0.99999971334842808) == 4.9999999999701759
    assert calcEmpiricalProbFromValue(2.5, 1e6, 10e6) == 0.82148367161911606
    assert calcEmpiricalValueFromProb(
        2.5, 1e6, 0.82148367161911606) == 10000000.00000999
    assert calcEmpiricalProbFromRange(
        2.5, 1e6, [0, 1]) == 1.6362032828176688e-08
    print('Passed testing all probs functions.')


if __name__ == '__main__':
    test()

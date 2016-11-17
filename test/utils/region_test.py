#!/usr/bin/env python

#stdlib imports
import urllib.request as request
import tempfile
import os.path
import sys

#hack the path so that I can debug these functions if I need to
homedir = os.path.dirname(os.path.abspath(__file__)) #where is this script?
pagerdir = os.path.abspath(os.path.join(homedir,'..','..'))
sys.path.insert(0,pagerdir) #put this at the front of the system path, ignoring any installed shakemap stuff

#third party imports 
import numpy as np

#local imports
from losspager.utils.region import PagerRegions

def test():
    pregions = PagerRegions()
    assert pregions.getRegion('NZ') == 1
    assert pregions.getRegion('AU') == 2
    assert pregions.getRegion('AI') == 3
    assert pregions.getRegion('AO') == 4
    assert pregions.getRegion('GT') == 5
    assert pregions.getRegion('SS') == 6

    assert pregions.getComment(1) == 'Overall, the population in this region resides in structures that are highly resistant to earthquake shaking, though some vulnerable structures exist.'
    assert pregions.getComment(2) == 'Overall, the population in this region resides in structures that are resistant to earthquake shaking, though vulnerable structures exist.'
    assert pregions.getComment(3) == 'Overall, the population in this region resides in structures that are a mix of vulnerable and earthquake resistant construction.'
    assert pregions.getComment(4) == 'Overall, the population in this region resides in structures that are vulnerable to earthquake shaking, though resistant structures exist.'
    assert pregions.getComment(5) == 'Overall, the population in this region resides in structures that are highly vulnerable to earthquake shaking, though some resistant structures exist.'
    assert pregions.getComment(6) == 'Overall, the population in this region resides in structures that are extremely vulnerable to earthquake shaking, though some resistant structures exist.'
    


if __name__ == '__main__':
    test()

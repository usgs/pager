#!/usr/bin/env python

# stdlib imports
import tempfile
import os.path
import sys
from collections import OrderedDict
import hashlib
import shutil

# third party imports
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# local imports
from losspager.vis.impactscale import drawImpactScale

matplotlib.use('Agg')


def img_test():
    # NOTE:  This isn't a great test, so I am turning it off for now,
    # until I can find a more reliable way to test images.
    testhash1 = b'\\\x03\xa9\x04\xe6\x8e\x99\x87r\xf2\xd9\xb9\xd9\xf8T\x83'
    testhash2 = b'\xe0\x19\xee$\x1a\xdcp\xdfX\x16\x8c\xb4\x95!t\xe0'
    testhash3 = b"xuw\xde0\x0c\xa23[P'\xf3\xab^\x9d\xb7"
    testhash4 = b'P\xcc\xc8n\xc2Z\x9fGH\x1d\x1cu\xd8\x00\x05n'
    try:
        homedir = tempfile.mkdtemp()
        ranges = OrderedDict([('0-1', 0.03),
                              ('1-10', 0.14),
                              ('10-100', 0.32),
                              ('100-1000', 0.325),
                              ('1000-10000', 0.15),
                              ('10000-100000', 0.03),
                              ('100000-10000000', 0.01)])
        f = drawImpactScale(ranges, 'economic', debug=False)
        outfile = os.path.join(homedir, 'test1.png')
        f.savefig(outfile)
        plt.close(f)
        data = open(outfile, 'rb').read()
        m = hashlib.md5()
        m.update(data)
        print('Testing first economic plot is consistent with prior results...')
        assert m.digest() == testhash1
        print('Passed.')

        ranges = OrderedDict([('0-1', 0.8),
                              ('1-10', 0.1),
                              ('10-100', 0.05),
                              ('100-1000', 0.03),
                              ('1000-10000', 0.02),
                              ('10000-100000', 0.0),
                              ('100000-10000000', 0.0)])
        f = drawImpactScale(ranges, 'fatality', debug=False)
        outfile = os.path.join(homedir, 'test2.png')
        f.savefig(outfile)
        plt.close(f)
        data = open(outfile, 'rb').read()
        m = hashlib.md5()
        m.update(data)
        print('Testing first fatality plot is consistent with prior results...')
        assert m.digest() == testhash2
        print('Passed.')

        ranges = OrderedDict([('0-1', 0.1),
                              ('1-10', 0.6),
                              ('10-100', 0.25),
                              ('100-1000', 0.03),
                              ('1000-10000', 0.02),
                              ('10000-100000', 0.0),
                              ('100000-10000000', 0.0)])
        f = drawImpactScale(ranges, 'fatality', debug=False)
        outfile = os.path.join(homedir, 'test3.png')
        f.savefig(outfile)
        plt.close(f)
        data = open(outfile, 'rb').read()
        m = hashlib.md5()
        m.update(data)
        print('Testing second fatality plot is consistent with prior results...')
        assert m.digest() == testhash3
        print('Passed.')

        ranges = OrderedDict([('0-1', 0.1),
                              ('1-10', 0.6),
                              ('10-100', 0.25),
                              ('100-1000', 0.03),
                              ('1000-10000', 0.0),
                              ('10000-100000', 0.45),
                              ('100000-10000000', 0.)])
        f = drawImpactScale(ranges, 'fatality', debug=False)
        outfile = os.path.join(homedir, 'test4.png')
        f.savefig(outfile)
        plt.close(f)
        data = open(outfile, 'rb').read()
        m = hashlib.md5()
        m.update(data)
        print('Testing third fatality plot is consistent with prior results...')
        assert m.digest() == testhash4
        print('Passed.')

    except Exception as error:
        raise error
    finally:
        if os.path.isdir(homedir):
            shutil.rmtree(homedir)


if __name__ == '__main__':
    img_test()

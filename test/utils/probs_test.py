#!/usr/bin/env python

# third party imports
import numpy as np

# local imports
from losspager.utils.probs import (phi,
                                   invphi,
                                   calcEmpiricalValueFromProb,
                                   calcEmpiricalProbFromRange,
                                   calcEmpiricalProbFromValue)


def test():
    print('Testing all probs functions...')
    np.testing.assert_almost_equal(phi(5.0), 0.99999971334842808)
    np.testing.assert_almost_equal(
        invphi(0.99999971334842808), 4.9999999999701759)
    np.testing.assert_almost_equal(
        calcEmpiricalProbFromValue(2.5, 1e6, 10e6), 0.82148367161911606)
    np.testing.assert_almost_equal(calcEmpiricalValueFromProb(
        2.5, 1e6, 0.82148367161911606), 10000000.00000999)
    np.testing.assert_almost_equal(calcEmpiricalProbFromRange(
        2.5, 1e6, [0, 1]), 1.6362032828176688e-08)
    print('Passed testing all probs functions.')


if __name__ == '__main__':
    test()

import numpy as np
import math
from scipy.special import erfc, erfcinv


def phi(input):
    """Phi function.

    :param input:
      Float (scalar or array) value.
    :returns:
      phi(input).
    """
    return 0.5 * erfc(-input / np.sqrt(2))


def invphi(input):
    """Inverse phi function.

    :param input:
      Float (scalar or array) value.
    :returns:
      invphi(input).
    """
    return -1 * np.sqrt(2) * erfcinv(input / 0.5)


def calcEmpiricalProbFromValue(G, e, value):
    """Calculate the empirical probability of a given value of loss (fatalities, dollars).

    :param G:
      Input G statistic.
    :param e:
      Expected number of losses.
    :param value:
      Number of losses for which corresponding probability should be calculated.
    :returns:
      Probability that value will not be exceeded.
    """
    e = e + 0.00001
    value = value + 0.00001
    p = phi((math.log(value) - math.log(e)) / G)
    return p


def calcEmpiricalValueFromProb(G, e, p):
    """Calculate the loss value given an input probability.

    :param G:
      Input G statistic.
    :param e:
      Expected number of losses.
    :param p:
      Input probability for which corresponding loss value should be calculated.
    :returns:
      Number of losses.
    """
    e = e + 0.00001
    value = math.exp(G * invphi(p) + math.log(e))
    return value


def calcEmpiricalProbFromRange(G, e, drange):
    """Calculate the empirical probability of a given loss range.

    :param G:
      Input G statistic.
    :param e:
      Expected number of losses.
    :param drange:
      Two-element sequence, containing range of losses over which probability should be calculated.
    :returns:
      Probability that losses will occur in input range.
    """
    e = e + 0.00001
    if e < 1:
        # e = 0.1
        if G > 1.7:
            G = 1.7613
    if len(drange) == 2:
        if (e - 0) < 0.001:
            e = 0.5
        fmin = drange[0] + 0.00001
        fmax = drange[1] + 0.00001
        p1 = phi((math.log(fmax) - math.log(e)) / G)
        p2 = phi((math.log(fmin) - math.log(e)) / G)
        p = p1 - p2
        return p
    else:
        psum = 0
        for i in range(0, len(drange) - 1):
            fmax = drange[i + 1] + 0.00001
            fmin = drange[i] + 0.00001
            p1 = phi((math.log(fmax) - math.log(e)) / G)
            p2 = phi((math.log(fmin) - math.log(e)) / G)
            psum += p1 - p2
        return psum

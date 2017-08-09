import numpy as np
from scipy.special import erfc, erfcinv
    
def phi(input):
    """Phi function.
    :param input: 
      Input value.
    :returns: 
      Phi(input).
    """    
    return 0.5 * erfc(-input/np.sqrt(2))

def invphi(input):
    """Inverse of Phi function.
    :param input: 
      Input value.
    :returns: 
      Inverse of Phi(input).
    """
    return -1 * np.sqrt(2) * erfcinv(input/0.5)

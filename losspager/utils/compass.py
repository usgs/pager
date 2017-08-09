#!/usr/bin/python

# third party imports
import numpy as np
from openquake.hazardlib.geo import geodetic

def get_compass_dir(lat1, lon1, lat2, lon2, format='short'):
    """Get the nearest string compass direction between two points.
    
    :param lat1: Latitude of first point.
    :param lon1: Longitude of first point.
    :param lat2: Latitude of second point.
    :param lon2: Longitude of second point.
    :param format: String used to determine the type of output. ('short','long').
    :returns: String compass direction, in the form of 'North','Northeast',... if format is 'long', 
             or 'N','NE',... if format is 'short'.
    """
    if format != 'short':
        points = ['North', 'Northeast', 'East', 'Southeast', 'South', 'Southwest', 'West', 'Northwest']
    else:
        points = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    az = geodetic.azimuth(lon1, lat1, lon2, lat2)
    angles = np.arange(0, 360, 45)
    adiff = abs(az - angles)
    i = adiff.argmin()
    return points[i]

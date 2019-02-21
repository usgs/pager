#!/usr/bin/env python

from mapio.gmt import GMTGrid
from mapio.gdal import GDALGrid


def get_file_type(file):
    """Internal method to figure out which file type (GMT or GDAL)
    the population/country code grid files are.
    """
    if GMTGrid.getFileType(file) == 'unknown':
        try:
            gdict = GDALGrid.getFileGeoDict(file)
            return GDALGrid
        except:
            pass
    else:
        return GMTGrid
    return None

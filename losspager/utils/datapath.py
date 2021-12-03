#!/usr/bin/env python

import os.path


def get_data_path(datafile):
    """Convenience function to allow scripts to retrieve the full path to a package data file/folder.

    :param datafile:
      Name of a data file (contents.xml, foo.txt, etc.)
    :returns:
      Full path to that file on the installed system.
    """
    homedir = os.path.dirname(os.path.abspath(__file__))  # where is this script?
    # the data directory should be one up and then down into data
    dpath = os.path.abspath(os.path.join(homedir, "..", "data", datafile))
    if not os.path.isfile(dpath) and not os.path.isdir(dpath):
        return None
    return dpath

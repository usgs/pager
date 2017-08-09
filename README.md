PAGER
=====


| Travis  | CodeCov |
| ------------- | ------------- |
| [![Build Status](https://travis-ci.org/usgs/pager.svg?branch=master)](https://travis-ci.org/usgs/pager)  | [![codecov](https://codecov.io/gh/usgs/pager/branch/master/graph/badge.svg)](https://codecov.io/gh/usgs/pager)  |

Prompt Assessment of Global Earthquakes for Response (PAGER)

The PAGER system provides fatality and economic loss impact estimates following significant earthquakes worldwide.

Command Line Programs
---------------------
 - `pager` This is the primary script to run PAGER.  It creates all output including onePAGER PDF.
   This script is meant to be run by the user.
   <pre>
   Basic usage:
   pager grid
    where grid can be either:
      - A path to a local ShakeMap grid.xml file.
      - An event ID (i.e., us2010abcd), which (on a primary system) will find the most recently PDL-downloaded grid file.
      - A url (http://earthquake.usgs.gov/realtime/product/shakemap/us10007tas/us/1484425631405/download/grid.xml)

   For full usage, type "pager --help".
   </pre>
 - `pagerlite` Ancillary script used to generate PAGER model results on the command line.
   This script is meant to be run by the user.
   Basic usage:
    pagerlite grid.xml

    will print out exposures (per-country, and total)...
    <pre>
    Country MMI1 MMI2 MMI3 MMI4 MMI5  MMI6   MMI7    MMI8   MMI9 MMI10
    AF         0    0   10  100 1000 10000 100000 1000000 100000     0
    PK         0    0   10  100 1000 10000 100000 1000000 100000     0
    Total      0    0   20  200 2000 20000 200000 2000000 200000     0

    For full usage, type "pagerlite --help".
    </pre>

 - `adminpager` Administrative script to manage PAGER production systems.
   This script is meant to be run by the user.
   <pre>
   There are a lot of options to this program, allowing the user to get the system status,
   archive/un-archive events, query the PAGER results on the file system, etc.

   For full usage, type "adminpager --help".
   </pre>
 - `mailadmin` Administrative script to manage PAGER user database on production systems. (User)
   This script is meant to be run by the user.
   <pre>
   There are a lot of options to this program, allowing the user to get the system (email) status,
   add/delete/list users, list event/version history, etc.

   For full usage, type "mailadmin --help".
   </pre>
 - `callpager` Script that sits in between PDL and the pager command line program on production systems.
   This script is meant to be run by the PDL process and is generally not run by the user.
 - `emailpager` Script that emails users when PAGER products appear in PDL. 
   This script is meant to be run by the PDL process and is generally not run by the user.
 - `hdfupdate` Script to be run when PAGER inventory spreadsheets have been updated in repository. (Developer)
   The HDF versions of the PAGER inventory are faster to read than Excel spreadsheets, so this script is used
   when the Excel versions have been modified and the HDF versions (both in the repository) need to be updated.
   This script is meant to be run by a developer.
 - `setup_env.sh` Bash script to create PAGER Python environment, including all Python dependencies.
   This script is meant to be run by a developer.
 - `updatepager` Script to update PAGER source code and (optionally) dependencies.
   This script is meant to be run by an end user.
 

Background
----------
The models implemented in this repository have been published in the papers listed here:

http://earthquake.usgs.gov/data/pager/references.php

primarily under the section titled "Loss and Impact Estimation".

PAGER Library Use
----------------------------
This library makes use of a number of third party libraries, as well as some USGS libraries. If
you wish to develop using PAGER as a library for loss modeling, the easiest path is to use the
setup_env.sh bash script included in the repository.  The required conda-installable packages
are found in that file, as well as some other packages that are found on GitHub and installed using
pip.

We hope soon to have more complete documentation for the PAGER loss models - for the time being, refer
to the GitHub repository file listings for API documentation, and the notebooks included in the
repository for example usage of the models.

As an example, you can see sample usage of the loss models by looking at this notebook:

https://github.com/usgs/pager/blob/master/notebooks/EarthquakeLosses.ipynb

In production, PAGER uses Landscan population data, which is available under license agreement
from Oakridge National Laboratory.  http://web.ornl.gov/sci/landscan/landscan_data_avail.shtml

It is *possible* to use other population gridded data sets, such as the CIESIN Gridded
Population of the World (GPW).  Use of a population data set other than Landscan will give different
results than that of the PAGER system run by the USGS.

http://sedac.ciesin.columbia.edu/data/collection/gpw-v3










  



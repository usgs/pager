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





Dependencies
------------
 - Non-Python Dependencies
  - LaTeX 
    - Mac OS: <a href="http://tug.org/mactex/downloading.html">http://tug.org/mactex/downloading.html</a>
    - RedHat (or derivative) Linux: sudo yum pdflatex

  - PDL: <a href="http://ehppdl1.cr.usgs.gov/userguide/install.html">http://ehppdl1.cr.usgs.gov/userguide/install.html</a>

 - Python Dependencies
   - git Source code control tool freely available for all platforms, probably already installed on newer versions
     of Linux and MacOS.  If not, obtain from https://git-scm.com/downloads


Installation
-------------
For a full install of PAGER, you will need to have a number of data files installed on your system.
Most of these files are obtainable for free from various sources on the Internet, with the exception of
Landscan data from Oakridge National Labs (see URL below).  Most of these mostly binary files were too
large to include in a git repository, so they have been bundled together internally for USGS use.

Required Files:
 - Country level administrative boundaries http://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/
 - Global cities file http://download.geonames.org/export/dump/cities1000.zip
 - Timezones file https://github.com/evansiroky/timezone-boundary-builder/releases
 - 


Contact mhearne@usgs.gov for information regarding the whereabouts of
these files.
To install the PAGDo the following (If you already have Anaconda or Miniconda installed, skip steps #2-3):

  1. git clone https://github.com/usgs/pager losspager
  2. curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh
  3. sh Miniconda2-latest-MacOSX-x86_64.sh
  4. cd losspager
  6. source deactivate #this turns off any current virtual environments you may have configured
  5. ./setup_env.sh
  6. source activate pager
  6. cd ..
  7. pip install losspager/







  



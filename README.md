PAGER
=====


| Travis  | CodeCov |
| ------------- | ------------- |
| [![Build Status](https://travis-ci.org/usgs/pager.svg?branch=master)](https://travis-ci.org/usgs/pager)  | [![codecov](https://codecov.io/gh/usgs/pager/branch/master/graph/badge.svg)](https://codecov.io/gh/usgs/pager)  |

Prompt Assessment of Global Earthquakes for Response (PAGER)

The PAGER system provides fatality and economic loss impact estimates following significant earthquakes worldwide.

Command Line Programs
---------------------
 - pager This is the primary script to run PAGER.  It creates all output including onePAGER PDF. (User)
   Basic usage:
   pager grid
    where grid can be either:
      - A path to a local ShakeMap grid.xml file.
      - An event ID (i.e., us2010abcd), which (on a primary system) will find the most recently PDL-downloaded grid file.
      - A url (http://earthquake.usgs.gov/realtime/product/shakemap/us10007tas/us/1484425631405/download/grid.xml)
 - pagerlite Ancillary script used to generate PAGER model results on the command line. No file output (User)
   Basic usage:
    pagerlite grid.xml

    will print out exposures (per-country, and total)...
    <pre>
    Country MMI1 MMI2 MMI3 MMI4 MMI5  MMI6   MMI7    MMI8   MMI9 MMI10
    AF         0    0   10  100 1000 10000 100000 1000000 100000     0
    PK         0    0   10  100 1000 10000 100000 1000000 100000     0
    Total      0    0   20  200 2000 20000 200000 2000000 200000     0
    <pre>

 - adminpager Administrative script to manage PAGER output on production systems. (User)
 - mailadmin Administrative script to manage PAGER user database on production systems. (User)
 - callpager Script that sits in between PDL and the pager command line program on production systems. (Automated)
 - emailpager Script that emails users when PAGER products appear in PDL. (Automated)
 - hdfupdate Script to be run when PAGER inventory spreadsheets have been updated in repository. (Developer)
 - setup_env.sh Bash script to create PAGER environment. (Developer)
 - updatepager Script to update PAGER source code and (optionally) dependencies. (User)
 

Background
----------
The models implemented in this repository have been published in the papers listed here:

http://earthquake.usgs.gov/data/pager/references.php

primarily under the section titled "Loss and Impact Estimation".



You will need to have a number of data files installed on your system.
Contact mhearne@usgs.gov for information regarding the whereabouts of
these files.

Non-Python Dependencies
----------------------
* LaTeX 
  * Mac OS: <a href="http://tug.org/mactex/downloading.html">http://tug.org/mactex/downloading.html</a>
  * RedHat Linux: sudo yum pdflatex

* PDL: <a href="http://ehppdl1.cr.usgs.gov/userguide/install.html">http://ehppdl1.cr.usgs.gov/userguide/install.html</a>

Python Dependencies
------------
Currently, to install the code and its dependencies requires use of git.

Do the following (If you already have Anaconda or Miniconda installed, skip steps #2-3):

  1. git clone https://github.com/usgs/pager losspager
  2. curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh
  3. sh Miniconda2-latest-MacOSX-x86_64.sh
  4. cd losspager
  6. source deactivate #this turns off any current virtual environments you may have configured
  5. ./setup_env.sh
  6. source activate pager
  6. cd ..
  7. pip install losspager/







  



PAGER
=====


| Travis  | CodeCov |
| ------------- | ------------- |
| [![Build Status](https://travis-ci.org/usgs/pager.svg?branch=master)](https://travis-ci.org/usgs/pager)  | [![codecov](https://codecov.io/gh/usgs/pager/branch/master/graph/badge.svg)](https://codecov.io/gh/usgs/pager)  |

Prompt Assessment of Global Earthquakes for Response (PAGER)

The PAGER system provides fatality and economic loss impact estimates following significant earthquakes worldwide.

Models
------
The models implemented in this repository have been published in the papers listed here:

http://earthquake.usgs.gov/data/pager/references.php

primarily under the section titled "Loss and Impact Estimation".


This will be the code behind the new PAGER system.  Dependencies include:

 - LaTeX
 - Product Distribution Layer (PDL)

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







  



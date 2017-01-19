#!/bin/bash

VENV=pager
PYVER=3.5

DEPARRAY=(numpy scipy matplotlib jupyter rasterio fiona xlrd xlwt pandas shapely h5py gdal descartes sphinx configobj pyproj pytest pytest-cov pytables pytest-mpl cartopy pyyaml rtree openpyxl pycrypto paramiko beautifulsoup4 docutils decorator nose mock cython)

#turn off whatever other virtual environment user might be in
source deactivate
    
#remove any previous virtual environments called pager
CWD=`pwd`
cd $HOME;
conda remove --name $VENV --all -y
cd $CWD
    
#create a new virtual environment called $VENV with the below list of dependencies installed into it
conda create --name $VENV --yes --channel conda-forge python=$PYVER ${DEPARRAY[*]} -y

#activate the new environment
source activate $VENV

#install some items separately
#conda install -y sqlalchemy #at the time of this writing, this is v1.0, and I want v1.1
conda install -y psutil

#do pip installs of those things that are not available via conda.
pip install 'SQLAlchemy==1.1.0b3' #installs any sqlalchemy greater than 1.1.0
pip install SQLAlchemy-Utils

#download openquake, install it using pip locally, ignore specified dependencies,
#as these should be installed using conda above
# wget --tries=3 https://github.com/gem/oq-hazardlib/archive/master.zip -O openquake.zip
# pip -v install --no-deps openquake.zip
# rm openquake.zip
pip install git+https://github.com/gem/oq-hazardlib.git

#download MapIO, install it using pip locally
# wget --tries=3 https://github.com/usgs/MapIO/archive/master.zip -O mapio.zip
# pip install mapio.zip
# rm mapio.zip
pip install git+https://github.com/usgs/MapIO.git

#download MapIO, install it using pip locally
# wget --tries=3 https://github.com/usgs/earthquake-impact-utils/archive/master.zip -O impact.zip
# pip install impact.zip
# rm impact.zip
pip install git+https://github.com/usgs/earthquake-impact-utils.git

pip install sphinx_rtd_theme
pip install flake8
pip install pep8-naming

#tell the user they have to activate this environment
echo "Type 'source activate ${VENV}' to use this new virtual environment."

#!/bin/bash

VENV=pager
PYVER=3.5

DEPARRAY=(numpy scipy matplotlib jupyter rasterio fiona xlrd xlwt pandas cartopy shapely h5py gdal==1.11.4 descartes sphinx configobj pyproj pytest pytables pytest pytest-cov pytest-mpl cartopy)

#turn off whatever other virtual environment user might be in
source deactivate
    
#remove any previous virtual environments called pager
CWD=`pwd`
cd $HOME;
conda remove --name $VENV --all -y
cd $CWD
    
#create a new virtual environment called $VENV with the below list of dependencies installed into it
conda create --name $VENV --yes --channel conda-forge python=3.5 ${DEPARRAY[*]} -y

#activate the new environment
source activate $VENV

#install some items separately
#conda install -y sqlalchemy #at the time of this writing, this is v1.0, and I want v1.1
conda install -y psutil

#do pip installs of those things that are not available via conda.
#do pip installs of those things that are not available via conda.
pip install 'SQLAlchemy==1.1.0b3' #installs any sqlalchemy greater than 1.1.0
pip install SQLAlchemy-Utils
pip -v install git+git://github.com/gem/oq-hazardlib.git
pip install git+git://github.com/usgs/MapIO.git
pip install git+git://github.com/usgs/earthquake-impact-utils.git
pip install sphinx_rtd_theme
pip install flake8
pip install pep8-naming

#tell the user they have to activate this environment
echo "Type 'source activate ${VENV}' to use this new virtual environment."

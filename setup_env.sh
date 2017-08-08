#!/bin/bash

VENV=pager
PYVER=3.6

DEPARRAY=(numpy=1.12.1 scipy=0.19.0 matplotlib=1.5.3 jupyter=1.0.0 \
               rasterio=0.36.0 fiona=1.7.6 xlrd=1.0.0 xlwt=1.2.0 \
               pandas=0.20.2 shapely=1.5.17 h5py=2.7.0 gdal=2.1.3 \
               pyproj=1.9.5.1 pytest=3.1.2 pytest-cov=2.5.1 \
               pytables=3.4.2 pytest-mpl=0.7 cartopy=0.15.1 \
               pyyaml=3.12 rtree=0.8.3 openpyxl=2.5.0a1 \
               pycrypto=2.6.1 paramiko=2.1.2 beautifulsoup4=4.5.3 \
               docutils=0.13.1 decorator=4.0.11 nose=1.3.7 mock=2.0.0 \
               cython=0.25.2 sqlalchemy=1.1.11 sqlalchemy-utils=0.32.12 \
         descartes=1.1.0)

#if we're already in an environment called pager, switch out of it so we can remove it
source activate root
    
#remove any previous virtual environments called pager
CWD=`pwd`
cd $HOME;
conda remove --name $VENV --all -y
cd $CWD
    
#create a new virtual environment called $VENV with the below list of dependencies installed into it
conda create --name $VENV --yes --channel conda-forge python=$PYVER ${DEPARRAY[*]} -y

if [ $? -eq 1 ];then
    echo "Environment creation failed - look at error message from conda create above."
    exit 1
fi

#activate the new environment
source activate $VENV

#install some items separately
conda install -y psutil=5.2.1

#do pip installs of those things that are not available via conda.
#we're using curl to fetch these zip files instead of pip because some
#of our systems fail on the pip command - using curl gives us more control
#over how long we wait for a download to complete, and how many tries before giving up
#on the download.

#download openquake, install it using pip locally, ignore specified dependencies,
#as these should be installed using conda above
curl --max-time 60 --retry 3 -L https://github.com/gem/oq-engine/archive/v2.5.0.zip -o openquake.zip
pip -v install --no-deps openquake.zip
rm openquake.zip

#download MapIO, install it using pip locally
curl --max-time 60 --retry 3 -L https://github.com/usgs/MapIO/archive/0.6.2.zip -o mapio.zip
pip install mapio.zip
rm mapio.zip

#download impactutils, install it using pip locally
curl --max-time 60 --retry 3 -L https://github.com/usgs/earthquake-impact-utils/archive/master.zip -o impact.zip
pip install impact.zip
rm impact.zip

#tell the user they have to activate this environment
echo "Type 'source activate ${VENV}' to use this new virtual environment."

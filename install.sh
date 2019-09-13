#!/bin/bash

unamestr=`uname`
if [ "$unamestr" == 'Linux' ]; then
    prof=~/.bashrc
    mini_conda_url=https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
    matplotlibdir=~/.config/matplotlib
    env_file=environment_linux.yml
elif [ "$unamestr" == 'FreeBSD' ] || [ "$unamestr" == 'Darwin' ]; then
    prof=~/.bash_profile
    mini_conda_url=https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
    matplotlibdir=~/.matplotlib
    env_file=environment_osx.yml
else
    echo "Unsupported environment. Exiting."
    exit
fi

source $prof

echo "Path:"
echo $PATH

VENV=pager

# Is the reset flag set?
reset=1
while getopts r FLAG; do
  case $FLAG in
    r)
        reset=1
        
      ;;
  esac
done


# create a matplotlibrc file with the non-interactive backend "Agg" in it.
if [ ! -d "$matplotlibdir" ]; then
    mkdir -p $matplotlibdir
fi
matplotlibrc=$matplotlibdir/matplotlibrc
if [ ! -e "$matplotlibrc" ]; then
    echo "backend : Agg" > "$matplotlibrc"
    echo "NOTE: A non-interactive matplotlib backend (Agg) has been set for this user."
elif grep -Fxq "backend : Agg" $matplotlibrc ; then
    :
elif [ ! grep -Fxq "backend" $matplotlibrc ]; then
    echo "backend : Agg" >> $matplotlibrc
    echo "NOTE: A non-interactive matplotlib backend (Agg) has been set for this user."
else
    sed -i '' 's/backend.*/backend : Agg/' $matplotlibrc
    echo "###############"
    echo "NOTE: $matplotlibrc has been changed to set 'backend : Agg'"
    echo "###############"
fi


# Is conda installed?
conda --version
if [ $? -ne 0 ]; then
    echo "No conda detected, installing miniconda..."

    curl $mini_conda_url -o miniconda.sh;
    echo "Install directory: $HOME/miniconda"

    bash miniconda.sh -f -b -p $HOME/miniconda

    # Need this to get conda into path
    . $HOME/miniconda/etc/profile.d/conda.sh

    rm miniconda.sh
else
    echo "conda detected, installing $VENV environment..."
fi

echo "PATH:"
echo $PATH
echo ""


# Choose an environment file based on platform
# only add this line if it does not already exist
grep "/etc/profile.d/conda.sh" $prof
if [ $? -ne 0 ]; then
    echo ". $HOME/miniconda/etc/profile.d/conda.sh" >> $prof
fi

# If the user has specified the -r (reset) flag, then create an
# environment based on only the named dependencies, without
# any versions of packages specified.
if [ $reset == 1 ]; then
    echo "Ignoring platform, letting conda sort out dependencies..."
    env_file=environment.yml
fi

# Start in conda base environment
echo "Activate base virtual environment"
conda activate base

# make sure conda is up to date
conda update -n base conda -y

# Remove any existing pager environments
conda remove -y --name $VENV --all

# define the list of packages
package_list='
  beautifulsoup4
  cartopy
  cython
  decorator
  descartes
  docutils
  fiona
  flake8
  gdal
  h5py
  hypothesis
  impactutils
  jupyter
  mapio
  matplotlib<2.3
  mock
  nose
  openpyxl
  openquake.engine
  pandas
  paramiko
  pip
  psutil
  pycrypto
  pyproj
  pytables
  python=3.6
  pytest
  pytest-cov
  pytest-mpl
  pyyaml
  rasterio
  rtree
  scipy
  shapely
  sqlalchemy
  sqlalchemy-utils
  xlrd
  xlwt'

# it seems now that some of the geospatial packages are more stable
# in the defaults channel, so let's set that as our preferred channel.
conda config --add channels 'conda-forge'
conda config --add channels 'defaults'
conda config --set channel_priority flexible

# Create a conda virtual environment
echo "Creating the $VENV virtual environment:"
conda create -n $VENV -y $package_list

# Bail out at this point if the conda create command fails.
# Clean up zip files we've downloaded
if [ $? -ne 0 ]; then
    echo "Failed to create conda environment.  Resolve any conflicts, then try again."
    exit
fi


# Activate the new environment
echo "Activating the $VENV virtual environment"
conda activate $VENV

# This package
echo "Installing ${VENV}..."
pip install -e .

# Install default profile
#python bin/sm_profile -c default -a

# Tell the user they have to activate this environment
echo "Type 'conda activate $VENV' to use this new virtual environment."

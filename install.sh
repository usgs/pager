#!/bin/bash

# comment
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

# echo "Path:"
# echo $PATH

VENV=pager


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

    curl -L $mini_conda_url -o miniconda.sh;
    echo "Install directory: $HOME/miniconda"

    bash miniconda.sh -f -b -p $HOME/miniconda

    # Need this to get conda into path
    . $HOME/miniconda/etc/profile.d/conda.sh

    rm miniconda.sh
else
    echo "conda detected, installing $VENV environment..."
fi

# echo "PATH:"
# echo $PATH
# echo ""


# Choose an environment file based on platform
# only add this line if it does not already exist
grep "/etc/profile.d/conda.sh" $prof
if [ $? -ne 0 ]; then
    echo ". $HOME/miniconda/etc/profile.d/conda.sh" >> $prof
fi



# Start in conda base environment
echo "Activate base virtual environment"
conda activate base

# make sure conda is up to date
# echo "Updating conda..."
# conda update -n base conda -y

# check to see if mamba is installed in the base environment
if ! command -v mamba &> /dev/null
then
    echo "Installing mamba into base environment..."
    conda install mamba -n base -c conda-forge -y
    echo "Done installing mamba."
else
    echo "Mamba already installed."
fi

# Remove any existing pager environments
echo "Removing existing ${VENV} environment..."
conda remove -y --name $VENV --all

# define the list of packages
package_list='
  cartopy=0.20.2
  fiona>=1.8.13
  flake8
  gdal=3.4.2
  h5py>=2.10.0
  impactutils
  jupyter
  lxml>=3.5
  mapio
  matplotlib>=3.5
  mock
  numpy=1.21
  openpyxl>=3.0
  openssl=1.1.1
  pandas>=1.4.2
  paramiko>=2.8.1
  pip
  psutil>=5.8.0
  pycrypto
  pyproj>=3.3.0
  pytables
  pytest
  pytest-cov
  pyyaml
  rasterio
  rtree
  scipy>=1.8.1
  shapely>=1.8.0
  sqlalchemy
  sqlalchemy-utils
  xlrd>=2.0.1
  xlwt'

# it seems now that some of the geospatial packages are more stable
# in the defaults channel, so let's set that as our preferred channel.
conda config --add channels 'conda-forge'
conda config --add channels 'defaults'
conda config --set channel_priority flexible

echo "Creating conda virtual environment..."
# Create a conda virtual environment
echo "Creating the $VENV virtual environment:"
conda create -n $VENV python=3.8 -y

# activate the new environment so mamba knows where to install packages
echo "Activating ${VENV} environment..."
conda activate $VENV

# Use mamba to install packages
echo "Using mamba to solve dependencies and install packages..."
mamba install -y $package_list


# Bail out at this point if the conda create command fails.
# Clean up zip files we've downloaded
if [ $? != 0 ]; then
    echo "Failed to create conda environment.  Resolve any conflicts, then try again."
    exit
fi

# Activate the new environment
echo "Activating the $VENV virtual environment"
conda activate $VENV

# This package
echo "Installing ${VENV}..."
pip install -e .

# test pager, if we get an error about libffi, try to fix it
# this is a total hack, but the only way I can see to get around 
# this weird result.
ffi_lib=libffi.so.7
pager_lib_dir=~/miniconda/envs/pager/lib
test_res=$(pager -h 2>&1)
echo $test_res | grep "${ffi_lib}"
if [ $? == 0 ]; then
    echo "Issue finding library ${ffi_lib}. Trying to resolve..."
    ffi_files=$(find ~/miniconda -name "libffi.so.7")
    if [ -z "$ffi_files" ]; then
        # this library is not found on the system
        echo "Cannot find missing library ${ffi_lib}. Please attempt to sort out libffi library issue."
        exit 1
    fi
    ffi_file=$(echo $ffi_files | head -1)
    echo "Copying ${ffi_file} to ${pager_lib_dir}..."
    cp $ffi_file $pager_lib_dir
    pager -h 2>/dev/null
    if [ $? != 0 ]; then
        echo "pager is still broken. Please address this manually."
        exit 1
    fi
fi

# Install default profile
#python bin/sm_profile -c default -a

# Tell the user they have to activate this environment
echo "Type 'conda activate $VENV' to use this new virtual environment."

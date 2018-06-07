#!/bin/bash

VENV=pager

unamestr=`uname`
if [ "$unamestr" == 'Linux' ]; then
    source ~/.bashrc
elif [ "$unamestr" == 'FreeBSD' ] || [ "$unamestr" == 'Darwin' ]; then
    source ~/.bash_profile
fi

# Is the reset flag set?
reset=0
while getopts r FLAG; do
  case $FLAG in
    r)
        reset=1
        
      ;;
  esac
done

echo "reset: $reset"

# create a matplotlibrc file with the non-interactive backend "Agg" in it.
if [ ! -d ~/.config/matplotlib ]; then
    mkdir -p ~/.config/matplotlib
    echo "backend : Agg" > ~/.config/matplotlib/matplotlibrc
fi

# Is conda installed?
conda --version
res=$?
echo "Conda: ${res}"
if [ $res -ne 0 ] ; then
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh \
        -O miniconda.sh;
    bash miniconda.sh -f -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
fi

# Choose OS-specific environment file, which specifies
# exact versions of all dependencies.
unamestr=`uname`
if [ "$unamestr" == 'Linux' ]; then
    env_file=environment_linux.yml
elif [ "$unamestr" == 'FreeBSD' ] || [ "$unamestr" == 'Darwin' ]; then
    env_file=environment_osx.yml
fi

# If the user has specified the -r (reset) flag, then create an
# environment based on only the named dependencies, without
# any versions of packages specified.
if [ $reset == 1 ]; then
    echo "Ignoring platform, letting conda sort out dependencies..."
    env_file=environment.yml
fi

echo "Environment file: $env_file"

# Turn off whatever other virtual environment user might be in
conda deactivate

# update the conda tool
# conda install conda=4.3.31 -y

# Create a conda virtual environment
echo "Creating the $VENV virtual environment:"
echo "conda env create -f $env_file --force"
conda env create -f $env_file --force

if [ $? -ne 0 ]; then
    echo "Failed to create conda environment.  Resolve any conflicts, then try again."
    echo "Cleaning up zip files..."
    exit
fi


# Activate the new environment
echo "Activating the $VENV virtual environment"
conda activate $VENV

# Install OpenQuake -- note that I have pulled this out of environment.yml
# because the requirements are too narrow to work with our other dependencies,
# but the openquake.hazardlib tests pass with this environment. We need to
# remember to check this when we change the environemnt.yml file though.
# conda install -y --force --no-deps -c conda-forge openquake.engine

if [ $? -ne 0 ]; then
    echo "Failed to install openquake.  Resolve any conflicts, then try again."
    echo "Cleaning up zip files..."
    exit
fi

# This package
echo "Installing pager..."
pip install -e .

# Install default profile
#python bin/sm_profile -c default -a

# Tell the user they have to activate this environment
echo "Type 'conda activate $VENV' to use this new virtual environment."

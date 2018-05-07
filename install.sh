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

# Is conda installed?
conda --version
res=$?
echo "Conda: ${res}"
if [ $? -ne 0 ] ; then
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

# Download dependencies not in conda or pypi
# Since we have SO many issues downloading zip files from github, I'm putting
# in a hack here to allow the developer to pre-download the zip files
# by hand in the repo directory.  Grr.
if [ ! -f impact-utils.zip ]; then
    curl --max-time 60 --retry 3 -L \
         https://github.com/usgs/earthquake-impact-utils/archive/0.8.zip -o impact-utils.zip
else
    echo "Skipping impact-utils.zip download, already present..."
fi

if [ ! -f mapio.zip ]; then
    curl --max-time 60 --retry 3 -L \
         https://github.com/usgs/MapIO/archive/0.7.2.zip -o mapio.zip
else
    echo "Skipping mapio.zip download, already present..."
fi


# Create a conda virtual environment
echo "Creating the $VENV virtual environment:"
conda env create -f $env_file --force

if [ $? -ne 0 ]; then
    echo "Failed to create conda environment.  Resolve any conflicts, then try again."
    echo "Cleaning up zip files..."
    rm impact-utils.zip
    rm mapio.zip
    exit
fi


# Activate the new environment
echo "Activating the $VENV virtual environment"
conda activate $VENV

# Install OpenQuake -- note that I have pulled this out of environment.yml
# because the requirements are too narrow to work with our other dependencies,
# but the openquake.hazardlib tests pass with this environment. We need to
# remember to check this when we change the environemnt.yml file though.
conda install -y --force --no-deps -c conda-forge openquake.engine

if [ $? -ne 0 ]; then
    echo "Failed to install openquake.  Resolve any conflicts, then try again."
    echo "Cleaning up zip files..."
    rm impact-utils.zip
    rm mapio.zip
    exit
fi

# Clean up downloaded packages
rm impact-utils.zip
rm mapio.zip

# This package
echo "Installing pager..."
pip install -e .

# Install default profile
#python bin/sm_profile -c default -a

# Tell the user they have to activate this environment
echo "Type 'conda activate $VENV' to use this new virtual environment."

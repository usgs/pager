#stdlib imports
import os.path
import shutil

#third party imports
import yaml

#local imports
from losspager.utils.exception import PagerException
def read_config():
    """Read in configuration parameters from config .py file.
    
    """
    #get config file name, make sure it exists
    configfilename = os.path.join(os.path.expanduser('~'),'.losspager','config.yml')
    if not os.path.isfile(configfilename):
        raise PagerException('Config file could not be found at %s.' % configfilename)

    config = yaml.load(open(configfilename,'rt'))
    return config

def write_config(config,make_backup=True):
    """Write out config parameters.

    :param config:
      Dictionary with configuration parameters.
    :param make_backup:
      Boolean indicating whether a backup of the current config file 
      should be made before writing new one.
    """
    #get config file name, make sure it exists
    configfilename = os.path.join(os.path.expanduser('~'),'.losspager','config.yml')
    if not os.path.isfile(configfilename):
        raise PagerException('Config file could not be found at %s.' % configfilename)
    backup_name = os.path.join(os.path.expanduser('~'),'.losspager','config.yml.bak')
    shutil.copyfile(configfilename,backup_name)
    f = open(configfilename,'wt')
    f.write(yaml.dump(config))
    f.close()

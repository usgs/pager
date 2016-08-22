from distutils.core import setup
import os.path

setup(name='losspager',
      version='0.1dev',
      description='USGS PAGER System',
      author='Mike Hearne',
      author_email='mhearne@usgs.gov',
      url='',
      packages=['losspager','losspager.models','losspager.utils','losspager.vis',
                'losspager.onepager','losspager.schema','losspager.mail'],
      package_data = {'losspager':[os.path.join('data', 'countries.csv')]},
      scripts = ['pagerlite','emailpager'],
)

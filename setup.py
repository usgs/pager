from distutils.core import setup
import os.path

setup(name='losspager',
      version='0.1dev',
      description='USGS PAGER System',
      author='Mike Hearne',
      author_email='mhearne@usgs.gov',
      url='',
      packages=['losspager','losspager.models','losspager.utils','losspager.vis',
                'losspager.onepager','losspager.schema','losspager.mail',
                'losspager.io'],
      package_data = {'losspager':[os.path.join('data', 'countries.xlsx'),
                                   os.path.join('data', 'API_NY.GDP.PCAP.CD_DS2_en_excel_v2.xls'),
                                   os.path.join('data', 'WPP2015_POP_F02_POPULATION_GROWTH_RATE.xls'),
                                   os.path.join('data', 'pager_regions.xlsx'),
                                   os.path.join('data', 'economy.xml'),
                                   os.path.join('data', 'expocat.csv'),
                                   os.path.join('data', 'fatality.xml'),
                                   os.path.join('data', 'onepager.tex'),
                                   os.path.join('data', 'semi_casualty.hdf'),
                                   os.path.join('data', 'semi_collapse_mmi.hdf'),
                                   os.path.join('data', 'semi_inventory.hdf'),
                                   os.path.join('data', 'semi_workforce.hdf'),
                                   os.path.join('logos', '*')
                                   ]},
      scripts = ['pagerlite','emailpager','pager','adminpager'],
)

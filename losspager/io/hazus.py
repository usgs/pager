# stdlib imports
from collections import OrderedDict
import os.path
import time
from urllib.request import urlopen
from urllib.parse import urljoin
import shutil

# third party imports
import fiona
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape as sShape
from shapely.geometry import Polygon as sPolygon
from shapely.geometry import GeometryCollection
from cartopy.io.shapereader import Reader
from cartopy.feature import ShapelyFeature
import cartopy.crs as ccrs
from bs4 import BeautifulSoup

# NEIC imports
from impactutils.mapping.mercatormap import MercatorMap
from impactutils.colors.cpalette import ColorPalette
from impactutils.mapping.city import Cities
from impactutils.textformat.text import (pop_round_short, commify)
from mapio.gdal import GDALGrid

# local imports
from losspager.vis.impactscale import GREEN, YELLOW, ORANGE, RED

MAX_TABLE_ROWS = 7  # number of rows in loss tables
TONS_PER_TRUCK = 25  # number of tons of debris per truckload
CENSUS_YEAR = '2010'

INJURIES = {'FEW': 12,
            'SEVERAL': 24,
            'DOZENS': 100,
            'HUNDREDS': 1000}
SHELTER = {'MINIMAL': 0.001,
           'CONSIDERABLE': 0.01}

RED_TAG_OFFSET = 12  # in pixels

FIGWIDTH = 7.0

# define the zorder values for various map components
STATE_ZORDER = 35
COUNTY_ZORDER = 20
TRACT_ZORDER = 30
NAME_ZORDER = 50
OCEAN_ZORDER = 40

WATERCOLOR = '#7AA1DA'
GREY = '#B4B4B4'

# define building types constants (the strings may change)
WOOD = 'Wood'
STEEL = 'Steel'
CONCRETE = 'Concrete'
PRECAST = 'Precast'
REINFORCED = 'Reinforced Masonry'
UNREINFORCED = 'Unreinforced Masonry'
MANUFACTURED = 'Manufactured Housing'

# names of files that can be fetched from the FEMA web site
LINKS = {'occupancy': 'building_damage_occup.txt',
         'county': 'county_results.txt',
         'tract': 'tract_results.txt'}


def fetch_hazus(url_or_dir, version_folder):
    files_retrieved = {}
    if os.path.isdir(url_or_dir):
        for key, link in LINKS.items():
            srcfile = os.path.join(url_or_dir, link)
            dstfile = os.path.join(version_folder, link)
            if os.path.isfile(srcfile):
                shutil.copyfile(srcfile, dstfile)
                files_retrieved[key] = dstfile
            else:
                files_retrieved[key] = False
        return files_retrieved

    fh = urlopen(url_or_dir)
    data = fh.read().decode('utf-8')
    fh.close()
    soup = BeautifulSoup(data, 'html.parser')

    for linkname, linkfile in LINKS.items():
        found_link = False
        for link in soup.find_all('a'):
            href = link.get('href')
            if linkfile in href:
                full_url = urljoin(url_or_dir, href)
                bytes = urlopen(full_url).read()
                outfile = os.path.join(version_folder, href)
                with open(outfile, 'wb') as f:
                    f.write(bytes)
                print('Wrote %s.' % outfile)
                files_retrieved[linkname] = outfile
                found_link = True
                break

    return files_retrieved


class HazusInfo(object):
    def __init__(self, version_folder, tract_csv,
                 county_file, occupancy_file):
        self._countyfile = county_file
        self._tractfile = tract_csv
        self._occupancy_file = occupancy_file

        # parse the county level data file
        self._dataframe = pd.read_csv(county_file,
                                      dtype={'CountyFips': object})
        self._dataframe = self._dataframe.sort_values('EconLoss',
                                                      ascending=False)
        self._ncounties = min(MAX_TABLE_ROWS, len(self._dataframe))
        homedir = os.path.dirname(os.path.abspath(__file__))
        datadir = os.path.join(homedir, '..', 'data')
        fipsfile = os.path.join(datadir, 'fips_codes.xlsx')
        fips = pd.read_excel(fipsfile, dtype={'FIPS': object})
        self._county_dict = {}
        for idx, row in fips.iterrows():
            key = row['FIPS']
            county = row['County'].replace('County', '').strip()
            state = row['StateAbbrev']
            value = (county, state)
            self._county_dict[key] = value

        # parse the tracts results, store as a dictionary of tract fips
        # and econ loss
        self._tract_loss = {}
        tracts = pd.read_csv(tract_csv, dtype={'Tract': object})
        for idx, row in tracts.iterrows():
            key = row['Tract']
            value = row['EconLoss']
            self._tract_loss[key] = value

        self.hazloss = self._dataframe['EconLoss'].sum()
        if self.hazloss < 1e3:
            self.summary_color = 'green'
        elif self.hazloss >= 1e3 and self.hazloss < 1e5:
            self.summary_color = 'yellow'
        elif self.hazloss >= 1e5 and self.hazloss < 1e6:
            self.summary_color = 'orange'
        else:
            self.summary_color = 'red'

    def createEconTable(self):
        table_lines = [
            '\\begin{tabularx}{\\barwidth}{lc*{1}{>{\\raggedleft\\arraybackslash}X}}']
        table_lines.append('\\hline')
        table_lines.append(
            '\\textbf{County} & \\textbf{State} & \\textbf{Total (\\textdollar M)} \\\\')
        table_lines.append('\\hline')
        total = self._dataframe['EconLoss'].sum()
        ntotal = len(self._dataframe)
        for i in range(0, self._ncounties):
            row = self._dataframe.iloc[i]
            county_name, state_abbrev = self._county_dict[row['CountyFips']]
            loss_str = pop_round_short(row['EconLoss'])[0:-1]
            line = '%s & %s & %s \\\\' % (county_name, state_abbrev, loss_str)
            table_lines.append(line)
        fmt = '\\multicolumn{2}{l}{\\textbf{Total (%i counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} \\\\'
        line = fmt % (ntotal, pop_round_short(total)[0:-1])
        table_lines.append(line)
        table_lines.append('\\hline')
        table_lines.append('\\end{tabularx}')
        table_text = '\n'.join(table_lines)
        return table_text

    def createInjuryTable(self):
        pop_total = pop_round_short(self._dataframe['Population'].sum())
        injured_total = pop_round_short(self._dataframe['NonFatal5p'].sum())
        table_lines = [
            '\\begin{tabularx}{\\barwidth}{lc*{2}{>{\\raggedleft\\arraybackslash}X}}']
        table_lines.append('\\hline')
        table_lines.append(
            '\\textbf{County} & \\textbf{State} & \\textbf{Population} & \\textbf{Total NFI} \\\\')
        table_lines.append('\\hline')
        ncounties = len(self._dataframe)
        for i in range(0, self._ncounties):
            row = self._dataframe.iloc[i]
            county_name, state_abbrev = self._county_dict[row['CountyFips']]
            pop = pop_round_short(row['Population'])
            injuries = pop_round_short(row['NonFatal5p'])
            fmt = '%s & %s & %s & %s \\\\'
            line = fmt % (county_name, state_abbrev,
                          pop, injuries)
            table_lines.append(line)
        fmt = '\\multicolumn{2}{l}{\\textbf{Total (%i counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} \\\\'
        line = fmt % (ncounties, pop_total, injured_total)
        table_lines.append(line)
        table_lines.append('\\hline')
        table_lines.append('\\end{tabularx}')
        table_text = '\n'.join(table_lines)
        return table_text

    def createShelterTable(self):
        house_total = pop_round_short(self._dataframe['Households'].sum())
        displaced_total = pop_round_short(self._dataframe['DisplHouse'].sum())
        shelter_total = pop_round_short(self._dataframe['Shelter'].sum())
        ncounties = len(self._dataframe)
        table_lines = [
            '\\begin{tabularx}{\\barwidth}{lc*{3}{>{\\raggedleft\\arraybackslash}X}}']
        table_lines.append('\\hline')
        table_lines.append(
            '\\               &                 & \\textbf{Total}  & \\textbf{Displ}  & \\textbf{People}  \\\\')
        table_lines.append(
            '\\               &                 & \\textbf{House-} & \\textbf{House-} & \\textbf{Needing} \\\\')
        table_lines.append(
            '\\textbf{County} & \\textbf{State} & \\textbf{holds}  & \\textbf{holds}  & \\textbf{Shelter} \\\\')
        table_lines.append('\\hline')
        for i in range(0, self._ncounties):
            row = self._dataframe.iloc[i]
            county_name, state_abbrev = self._county_dict[row['CountyFips']]
            households = pop_round_short(row['Households'])
            displaced = pop_round_short(row['DisplHouse'])
            shelter = pop_round_short(row['Shelter'])
            fmt = '%s & %s & %s & %s & %s \\\\'
            line = fmt % (county_name, state_abbrev,
                          households, displaced, shelter)
            table_lines.append(line)
        fmt = '\\multicolumn{2}{l}{\\textbf{Total (%i counties)}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} & \\multicolumn{1}{>{\\raggedleft}X}{\\textbf{%s}} \\\\'
        line = fmt % (ncounties, house_total, displaced_total, shelter_total)
        table_lines.append(line)
        table_lines.append('\\hline')
        table_lines.append('\\end{tabularx}')
        table_text = '\n'.join(table_lines)
        return table_text

    def createDebrisTable(self):
        wood = self._dataframe['DebrisW'].sum()/1e3  # values are in thousands
        steel = self._dataframe['DebrisS'].sum()/1e3
        wood_total = '%.3f' % wood
        steel_total = '%.3f' % steel
        debris_total = '%.3f' % (wood + steel)
        table_lines = [
            '\\begin{tabularx}{\\barwidth}{l*{1}{>{\\raggedleft\\arraybackslash}X}}']
        table_lines.append('\\hline')
        table_lines.append('\\                 & \\textbf{Tons}      \\\\')
        table_lines.append('\\textbf{Category} & \\textbf{(millions)} \\\\')
        table_lines.append('\\hline')

        table_lines.append('Brick / Wood & %s \\\\' % wood_total)
        table_lines.append(
            'Reinforced Concrete / Steel & %s \\\\' % steel_total)
        table_lines.append('\\textbf{Total} & \\textbf{%s} \\' % debris_total)
        table_lines.append('&  \\\\')
        table_lines.append('&  \\\\')
        trucks = commify(int(round(((wood + steel)*1e6)/25)))
        fmt = '\\textbf{Truck Loads (@25 tons/truck)} & \\textbf{%s} \\'
        line = fmt % trucks
        table_lines.append(line)
        table_lines.append('\\end{tabularx}')
        table_text = '\n'.join(table_lines)
        return table_text

    def drawHazusMap(self, shakegrid, filename, model_config):
        gd = shakegrid.getGeoDict()

        # Retrieve the epicenter - this will get used on the map (??)
        center_lat = shakegrid.getEventDict()['lat']
        center_lon = shakegrid.getEventDict()['lon']

        # load the ocean grid file (has 1s in ocean, 0s over land)
        # having this file saves us almost 30 seconds!
        # oceangrid = GDALGrid.load(oceangridfile,
        #                           samplegeodict=gd, resample=True)

        # define the map
        # first cope with stupid 180 meridian
        height = (gd.ymax-gd.ymin)*111.191
        if gd.xmin < gd.xmax:
            width = (gd.xmax-gd.xmin)*np.cos(np.radians(center_lat))*111.191
            xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
        else:
            xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
            xmax += 360
            width = ((gd.xmax+360) - gd.xmin) * \
                np.cos(np.radians(center_lat))*111.191

        aspect = width/height

        # if the aspect is not 1, then trim bounds in
        # x or y direction as appropriate
        if width > height:
            dw = (width - height)/2.0  # this is width in km
            xmin = xmin + dw/(np.cos(np.radians(center_lat))*111.191)
            xmax = xmax - dw/(np.cos(np.radians(center_lat))*111.191)
            width = (xmax-xmin)*np.cos(np.radians(center_lat))*111.191
        if height > width:
            dh = (height - width)/2.0  # this is width in km
            ymin = ymin + dh/111.191
            ymax = ymax - dh/111.191
            height = (ymax-ymin)*111.191

        aspect = width/height
        figheight = FIGWIDTH/aspect
        bounds = (xmin, xmax, ymin, ymax)
        figsize = (FIGWIDTH, figheight)

        # load the counties here so we can grab the county names to
        # draw on the map
        counties_file = model_config['counties']
        counties_shapes = fiona.open(counties_file, 'r')
        counties = counties_shapes.items(bbox=(xmin, ymin, xmax, ymax))
        county_shapes = []

        county_columns = {'name': [],
                          'lat': [],
                          'lon': [],
                          'pop': [],
                          }

        for cid, county in counties:
            # county is a dictionary
            county_shape = sShape(county['geometry'])
            state_fips = county['properties']['STATEFP10']
            county_fips = county['properties']['COUNTYFP10']
            fips = state_fips + county_fips
            df = self._dataframe
            weight = 1
            if (df['CountyFips'] == fips).any():
                loss_row = df[df['CountyFips'] == fips].iloc[0]
                weight = loss_row['EconLoss']
            center_point = county_shape.centroid
            county_name = county['properties']['NAMELSAD10'].replace(
                'County', '').strip()
            # feature = ShapelyFeature([county_shape], ccrs.PlateCarree(),
            #                          zorder=COUNTY_ZORDER)
            county_shapes.append(county_shape)
            county_columns['name'].append(county_name)
            county_columns['pop'].append(county_shape.area * weight)
            county_columns['lat'].append(center_point.y)
            county_columns['lon'].append(center_point.x)
            # ax.add_feature(feature, facecolor=GREY,
            #                edgecolor='grey', linewidth=0.5)
            # tx, ty = mmap.proj.transform_point(
            #     center_point.x, center_point.y, ccrs.PlateCarree())
            # plt.text(tx, ty, county_name,
            #          zorder=NAME_ZORDER,
            #          horizontalalignment='center',
            #          verticalalignment='center')

        # Create the MercatorMap object, which holds a separate but identical
        # axes object used to determine collisions between city labels.
        # here we're pretending that county names are city names.
        county_df = pd.DataFrame(county_columns)
        cities = Cities(county_df)
        mmap = MercatorMap(bounds, figsize, cities, padding=0.5)
        fig = mmap.figure
        ax = mmap.axes
        geoproj = mmap.geoproj
        # this needs to be done here so that city label collision
        # detection will work
        fig.canvas.draw()

        # draw county names
        mmap.drawCities(zorder=NAME_ZORDER)

        # now draw the counties in grey
        for county_shape in county_shapes:
            feature = ShapelyFeature([county_shape], ccrs.PlateCarree(),
                                     zorder=COUNTY_ZORDER)
            ax.add_feature(feature, facecolor=GREY,
                           edgecolor='grey', linewidth=0.5,
                           zorder=COUNTY_ZORDER)

        # now draw the county boundaries only so that we can see
        # them on top of the colored tracts.
        for county_shape in county_shapes:
            feature = ShapelyFeature([county_shape], ccrs.PlateCarree(),
                                     zorder=COUNTY_ZORDER)
            ax.add_feature(feature, facecolor=(0, 0, 0, 0),
                           edgecolor='grey', linewidth=0.5,
                           zorder=NAME_ZORDER)

        # define bounding box we'll use to clip vector data
        bbox = (xmin, ymin, xmax, ymax)

        # load and clip ocean vectors to match map boundaries
        oceanfile = model_config['ocean_vectors']
        oceanshapes = _clip_bounds(bbox, oceanfile)
        ax.add_feature(ShapelyFeature(oceanshapes, crs=geoproj),
                       facecolor=WATERCOLOR, zorder=OCEAN_ZORDER)

        # draw states with black border - TODO: Look into
        states_file = model_config['states']
        transparent = '#00000000'
        states = _clip_bounds(bbox, states_file)
        ax.add_feature(ShapelyFeature(states, crs=geoproj),
                       facecolor=transparent, edgecolor='k',
                       zorder=STATE_ZORDER)

        # draw census tracts, colored by loss level
        tracts_file = model_config['tracts']
        tract_shapes = fiona.open(tracts_file, 'r')
        tracts = tract_shapes.items(bbox=(xmin, ymin, xmax, ymax))
        ntracts = 0
        for tid, tract in tracts:
            # tract is a dictionary
            ntracts += 1
            tract_shape = sShape(tract['geometry'])
            state_fips = tract['properties']['STATEFP10']
            county_fips = state_fips + tract['properties']['COUNTYFP10']
            fips_column = self._dataframe['CountyFips']
            if not fips_column.str.contains(county_fips).any():
                continue
            tract_fips = county_fips + tract['properties']['TRACTCE10']
            econloss = 0.0
            if tract_fips in self._tract_loss:
                econloss = self._tract_loss[tract_fips]
            if econloss < 1e3:
                color = GREEN
            elif econloss >= 1e3 and econloss < 1e5:
                color = YELLOW
            elif econloss >= 1e5 and econloss < 1e6:
                color = ORANGE
            else:
                color = RED
            feature = ShapelyFeature([tract_shape], ccrs.PlateCarree(),
                                     zorder=TRACT_ZORDER)
            ax.add_feature(feature, facecolor=color)

        # # Draw the epicenter as a black star
        # plt.plot(center_lon, center_lat, 'k*', markersize=16,
        #          zorder=EPICENTER_ZORDER, transform=geoproj)

        # save our map out to a file
        print('Saving to %s' % filename)
        t0 = time.time()
        plt.savefig(filename)
        t1 = time.time()
        print('Done saving map - %.2f seconds' % (t1-t0))

    def createTaggingTables(self):
        df = pd.read_csv(self._occupancy_file)
        other_res = df[df.Occupancy.str.contains('^RES')]
        mfilter = other_res.Occupancy.str.contains('RES1 ')

        types_dict = OrderedDict()
        types_dict['Residential'] = other_res[~mfilter]
        types_dict['Single Family'] = df[df['Occupancy'] == 'RES1 ']
        types_dict['Commercial'] = df[df.Occupancy.str.contains('^COM')]
        types_dict['Industrial'] = df[df.Occupancy.str.contains('^IND')]
        types_dict['Education'] = df[df.Occupancy.str.contains('^EDU')]
        types_dict['Agriculture'] = df[df.Occupancy.str.contains('^AGR')]
        types_dict['Government'] = df[df.Occupancy.str.contains('^GOV')]

        green_dict = OrderedDict()
        for key, df in types_dict.items():
            green_dict[key] = df['GreenTag'].sum()

        yellow_dict = OrderedDict()
        for key, df in types_dict.items():
            yellow_dict[key] = df['YellowTag'].sum()

        red_dict = OrderedDict()
        for key, df in types_dict.items():
            red_dict[key] = df['RedTag'].sum()

        green_tag_table = self.create_tag_table(green_dict, 'INSPECTED')
        yellow_tag_table = self.create_tag_table(yellow_dict, 'RESTRICTED USE')
        red_tag_table = self.create_tag_table(red_dict, 'UNSAFE')
        return (green_tag_table, yellow_tag_table, red_tag_table)

    def create_tag_table(self, tag_dict, title):
        table_lines = ['\\begin{tabularx}{3.4cm}{lr}']
        table_lines.append('& \\\\')
        table_lines.append('\\multicolumn{2}{c}{\\textbf{%s}} \\\\' % title)
        table_lines.append('\\textbf{Occupancy} & \\textbf{\\# of tags}  \\\\')
        for key, value in tag_dict.items():
            line = '%s & %s \\\\' % (key, pop_round_short(value))
            table_lines.append(line)
        table_lines.append('\\end{tabularx}')
        table_text = '\n'.join(table_lines)
        return table_text


def _clip_bounds(bbox, filename):
    """Clip input fiona-compatible vector file to input bounding box.
    :param bbox:
      Tuple of (xmin,ymin,xmax,ymax) desired clipping bounds.
    :param filename:
      Input name of file containing vector data in a format compatible with fiona.
    :returns:
      Shapely Geometry object (Polygon or MultiPolygon).
    """
    f = fiona.open(filename, 'r')
    shapes = list(f.items(bbox=bbox))
    xmin, ymin, xmax, ymax = bbox
    newshapes = []
    bboxpoly = sPolygon([(xmin, ymax), (xmax, ymax),
                         (xmax, ymin), (xmin, ymin), (xmin, ymax)])
    for tshape in shapes:
        myshape = sShape(tshape[1]['geometry'])
        intshape = myshape.intersection(bboxpoly)
        newshapes.append(intshape)
        newshapes.append(myshape)
    gc = GeometryCollection(newshapes)
    f.close()
    return gc

# third party imports
import fiona
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape
from cartopy.feature import ShapelyFeature
from cartopy.io.shapereader import Reader
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# NEIC imports
from impactutils.mapping.mercatormap import MercatorMap
from impactutils.mapping.city import Cities
from impactutils.textformat.text import (round_to_nearest,
                                         pop_round_short,
                                         commify)

# local imports
from losspager.vis.impactscale import GREEN,YELLOW,ORANGE,RED

MAX_TABLE_ROWS = 7 # number of rows in loss tables
TONS_PER_TRUCK = 25 # number of tons of debris per truckload
CENSUS_YEAR = '2010'

INJURIES = {'FEW':12,
            'SEVERAL':24,
            'DOZENS':100,
            'HUNDREDS':1000}
SHELTER = {'MINIMAL':0.001,
           'CONSIDERABLE':0.01}

RED_TAG_OFFSET = 12 # in pixels

FIGWIDTH = 7.0

# define the zorder values for various map components
POP_ZORDER = 8
COAST_ZORDER = 11
LANDC_ZORDER = 10
OCEANC_ZORDER = 11
CLABEL_ZORDER = 50
OCEAN_ZORDER = 10
GRID_ZORDER = 20
EPICENTER_ZORDER = 30
CITIES_ZORDER = 12
WATERMARK_ZORDER = 60

# define building types constants (the strings may change)
WOOD = 'Wood'
STEEL = 'Steel'
CONCRETE = 'Concrete'
PRECAST = 'Precast'
REINFORCED = 'Reinforced Masonry'
UNREINFORCED = 'Unreinforced Masonry'
MANUFACTURED = 'Manufactured Housing'

class HazusInfo(object):
    def __init__(self,tract_shapefile,county_shapefile,occupancy_file,type_file):
        self._countyfile = county_shapefile
        self._tractfile = tract_shapefile
        self._occupancy_file = occupancy_file
        self._type_file = type_file

        # read all the properties in the county-level shapefile
        shapes = fiona.open(county_shapefile,'r')
        schema = shapes.schema['properties']
        self._dataframe = pd.DataFrame(columns=list(schema.keys()))
        for shape in shapes:
            self._dataframe = self._dataframe.append(shape['properties'],ignore_index=True)

        shapes.close()
        self._dataframe = self._dataframe.sort_values('EconLoss',ascending=False)
        self._ncounties = min(MAX_TABLE_ROWS,len(self._dataframe))

    def drawHazusMap(self,shakegrid,filename):
        gd = shakegrid.getGeoDict()

        # Retrieve the epicenter - this will get used on the map (??)
        center_lat = shakegrid.getEventDict()['lat']
        center_lon = shakegrid.getEventDict()['lon']

         # load the ocean grid file (has 1s in ocean, 0s over land)
         # having this file saves us almost 30 seconds!
        # oceangrid = GDALGrid.load(oceangridfile, samplegeodict=gd, resample=True)

        # define the map
        # first cope with stupid 180 meridian 
        height = (gd.ymax-gd.ymin)*111.191
        if gd.xmin < gd.xmax:
            width = (gd.xmax-gd.xmin)*np.cos(np.radians(center_lat))*111.191
            xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
        else:
            xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
            xmax += 360
            width = ((gd.xmax+360) - gd.xmin)*np.cos(np.radians(center_lat))*111.191

        aspect = width/height

        # if the aspect is not 1, then trim bounds in x or y direction as appropriate
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
        bbox = (xmin, ymin, xmax, ymax)
        bounds = (xmin, xmax, ymin, ymax)
        figsize = (FIGWIDTH, figheight)

        # Create the MercatorMap object, which holds a separate but identical
        # axes object used to determine collisions between city labels.
        cities = Cities.fromDefault()
        mmap = MercatorMap(bounds, figsize, cities, padding=0.5)
        fig = mmap.figure
        ax = mmap.axes
        geoproj = mmap.geoproj
        # this needs to be done here so that city label collision detection will work
        fig.canvas.draw()

        # draw standard map stuff
        ax.coastlines(resolution="10m", zorder=COAST_ZORDER);
        states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none')

        ax.add_feature(states_provinces, edgecolor='black',zorder=COAST_ZORDER)
        
        # draw census tracts, colored by loss level
        tracts = fiona.open(self._tractfile,'r')
        i = 1
        for tract in tracts:
            # print('Tract %i of %i' % (i,len(tracts)))
            i += 1
            # tract is a dictionary
            tract_shape = shape(tract['geometry'])
            econloss = tract['properties']['EconLoss']*1e6
            if econloss < 1e6:
                color = GREEN
            elif econloss >= 1e6 and econloss < 1e8:
                color = YELLOW
            elif econloss >= 1e8 and econloss < 1e9:
                color = ORANGE
            else:
                color = RED
            feature = ShapelyFeature([tract_shape],ccrs.PlateCarree())
            ax.add_feature(feature,facecolor=color)

        blankcolor = (0,0,0,0)
        counties = fiona.open(self._countyfile,'r')
        for county in counties:
            # county is a dictionary
            county_shape = shape(county['geometry'])
            center_point = county_shape.centroid
            county_name = county['properties']['CountyName']
            feature = ShapelyFeature([county_shape],ccrs.PlateCarree())
            ax.add_feature(feature,facecolor=blankcolor,edgecolor='k',linewidth=0.5)
            tx,ty = mmap.proj.transform_point(center_point.x,center_point.y,ccrs.PlateCarree())
            plt.text(tx,ty,county_name,
                     horizontalalignment='center',
                     verticalalignment='center')
            
        # # draw counties
        # blankcolor = (0,0,0,0)
        # counties = ShapelyFeature(Reader(self._countyfile).geometries(),
        #                           ccrs.PlateCarree(),
        #                           edgecolor='black',
        #                           linewidth=1.0,
        #                           facecolor=blankcolor,
        #                           linestyle='solid')
        # # linewidth doesn't really seem to change...
        # ax.add_feature(counties,zorder=100)

        # draw counties, colored by economic loss
        # counties = fiona.open(self._countyfile,'r')
        # i = 1
        # for county in counties:
        #     # print('County %i of %i' % (i,len(counties)))
        #     i += 1
        #     # county is a dictionary
        #     county_shape = shape(county['geometry'])
        #     center_point = county_shape.centroid
        #     county_name = county['properties']['CountyName']
        #     econloss = county['properties']['EconLoss']*1e6
        #     print(county_name,econloss)
        #     if econloss < 1e6:
        #         color = GREEN
        #     elif econloss >= 1e8 and econloss < 1e10:
        #         color = YELLOW
        #     elif econloss >= 1e10 and econloss < 1e9:
        #         color = ORANGE
        #     else:
        #         color = RED
        #     feature = ShapelyFeature([county_shape],ccrs.PlateCarree())
        #     ax.add_feature(feature,facecolor=color,edgecolor='k',linewidth=0.5)
        #     tx,ty = mmap.proj.transform_point(center_point.x,center_point.y,ccrs.PlateCarree())
        #     plt.text(tx,ty,county_name,
        #              horizontalalignment='center',
        #              verticalalignment='center')
        
        # Draw the epicenter as a black star
        plt.plot(center_lon, center_lat, 'k*', markersize=16, zorder=EPICENTER_ZORDER, transform=geoproj)
        
        # save our map out to a file
        print('Saving to %s' % filename)
        plt.savefig(filename)
            
    def plotTypeTagging(self,filename):
        df = pd.read_csv(self._type_file)
        wood = df[df.Type.str.contains(WOOD)]
        steel = df[df.Type.str.contains(STEEL)]
        concrete = df[df.Type.str.contains(CONCRETE)]
        precast = df[df.Type.str.contains(PRECAST)]
        reinforced = df[df.Type.str.contains(REINFORCED)]
        unreinforced = df[df.Type.str.contains(UNREINFORCED)]
        manufactured = df[df.Type.str.contains(MANUFACTURED)]

        wood_sum_yellow,wood_sum_red,nwood = get_column_tags(wood)
        steel_sum_yellow,steel_sum_red,nsteel = get_column_tags(steel)
        concrete_sum_yellow,concrete_sum_red,nconcrete = get_column_tags(concrete)
        precast_sum_yellow,precast_sum_red,nprecast = get_column_tags(precast)
        reinforced_sum_yellow,reinforced_sum_red,nreinforced = get_column_tags(reinforced)
        unreinforced_sum_yellow,unreinforced_sum_red,nunreinforced = get_column_tags(unreinforced)
        manufactured_sum_yellow,manufactured_sum_red,nmanufactured = get_column_tags(manufactured)
        heights = [('Wood',wood_sum_yellow,wood_sum_red,nwood),
                  ('Steel',steel_sum_yellow,steel_sum_red,nsteel),
                  ('Conc.',concrete_sum_yellow,concrete_sum_red,nconcrete),
                  ('Precast',precast_sum_yellow,precast_sum_red,nprecast),
                  ('Reinf.',reinforced_sum_yellow,reinforced_sum_red,nreinforced),
                  ('Unreinf.',unreinforced_sum_yellow,unreinforced_sum_red,nunreinforced),
                  ('Manuf.',manufactured_sum_yellow,manufactured_sum_red,nmanufactured)]
        
        _plot_tagging(heights,filename)
            
    def plotTagging(self,filename):
        df = pd.read_csv(self._occupancy_file)
        other_res = df[df.Occupancy.str.contains('^RES')]
        mfilter = other_res.Occupancy.str.contains('RES1 ')
        
        residential = other_res[~mfilter]
        commercial = df[df.Occupancy.str.contains('^COM')]
        industrial = df[df.Occupancy.str.contains('^IND')]
        single_family = df[df['Occupancy'] == 'RES1 ']
        religious = df[df.Occupancy.str.contains('^REL')]
        agriculture = df[df.Occupancy.str.contains('^AGR')]
        education = df[df.Occupancy.str.contains('^EDU')]
        government = df[df.Occupancy.str.contains('^GOV')]

        res_sum_yellow,res_sum_red,nres = get_column_tags(residential)
        com_sum_yellow,com_sum_red,ncom = get_column_tags(commercial)
        ind_sum_yellow,ind_sum_red,nind = get_column_tags(industrial)
        rel_sum_yellow,rel_sum_red,nrel = get_column_tags(religious)
        agr_sum_yellow,agr_sum_red,nagr = get_column_tags(agriculture)
        edu_sum_yellow,edu_sum_red,nedu = get_column_tags(education)
        gov_sum_yellow,gov_sum_red,ngov = get_column_tags(government)
        single_sum_yellow,single_sum_red,nsingle = get_column_tags(single_family)
        heights = [('Res',res_sum_yellow,res_sum_red,nres),
                  ('Com',com_sum_yellow,com_sum_red,ncom),
                  ('Ind',ind_sum_yellow,ind_sum_red,nind),
                  ('Single',single_sum_yellow,single_sum_red,nsingle),
                  ('Agr',agr_sum_yellow,agr_sum_red,nagr),
                  ('Edu.',edu_sum_yellow,edu_sum_red,nedu),
                  ('Gov',gov_sum_yellow,gov_sum_red,ngov)]
            
        _plot_tagging(heights,filename)

    def getLosses(self):
        losscols = ['CountyName','State','Population','EconLoss']
        losstable = self._dataframe[losscols].iloc[0:MAX_TABLE_ROWS]
        losstable['EconLoss'] /= 1000 #convert to billions of dollars
        total = self._dataframe['EconLoss'].sum()/1000.0
        return (losstable,total)

    def getInjuries(self):
        hurtcols = ['CountyName','State','Population','NonFatal5p']
        hurt_table = self._dataframe[hurtcols].iloc[0:MAX_TABLE_ROWS]
        total_hurt = self._dataframe['NonFatal5p'].sum()
        total_pop = self._dataframe['Population'].sum()
        totals = {'Population':total_pop,
                  'Injuries':total_hurt}
        return (hurt_table,totals)

    def getShelterNeeds(self):
        shelcols = ['CountyName','State',
                    'Households','DisplHouse','Shelter']
        sheltable = self._dataframe[shelcols].iloc[0:MAX_TABLE_ROWS]
        totals = {'Households':self._dataframe['Households'].sum(),
                  'DisplHouse':self._dataframe['DisplHouse'].sum(),
                  'Shelter':self._dataframe['Shelter'].sum()}
        return (sheltable,totals)

    def getDebris(self):
        brick_wood_debris = self._dataframe['DebrisW'].sum()
        concrete_steel_debris = self._dataframe['DebrisS'].sum()
        all_debris = brick_wood_debris + concrete_steel_debris
        table = pd.DataFrame(columns=['category','megatons'])
        table = table.append({'category':'Brick / Wood',
                              'megatons' : brick_wood_debris},
                              ignore_index=True)
        table = table.append({'category':'Reinforced Concrete / Steel',
                              'megatons' : concrete_steel_debris},
                              ignore_index=True)
        truck_loads = all_debris * 1/TONS_PER_TRUCK * 1000
        totals = {'megatons':all_debris,
                 'truckloads':truck_loads}
        
        return (table,totals)

    def getLossTable(self):
        losstable,total = self.getLosses()
        tabledata = ""
        for idx,lossrow in losstable.iterrows():
            econloss = int(np.round(lossrow['EconLoss']))
            tpl = (lossrow['CountyName'],lossrow['State'],
                   econloss)
            fmt = '%s & %s & %i \\\\' + '\n'
            row = fmt % tpl
            tabledata = tabledata + row

        int_total = int(np.round(total))
        row = '\\textbf{Total} & & \\textbf{%s} \\' % ("{:,}".format(int_total))
        tabledata = tabledata + row
        return tabledata

    def getInjuryTable(self):
        hurt_table,totals = self.getInjuries()
        tabledata = ""
        for idx,hurtrow in hurt_table.iterrows():
            kilopop = pop_round_short(hurtrow['Population'])
            hurt = int(np.round(hurtrow['NonFatal5p']))
            tpl = (hurtrow['CountyName'],hurtrow['State'],
                   kilopop, hurt)
            fmt = '%s & %s & %s & %i \\\\' + '\n'
            row = fmt % tpl
            tabledata = tabledata + row

        kilototal = pop_round_short(totals['Population'])
        inj_total = pop_round_short(totals['Injuries'])
        fmt = '\\textbf{Total} & & \\textbf{%s} & \textbf{%s} \\\\'
        tpl =  (kilototal,inj_total)
        row = fmt % tpl
        tabledata = tabledata + row
        return tabledata

    def getShelterTable(self):
        shel_table,totals = self.getShelterNeeds()
        tabledata = ""
        for idx,shelrow in shel_table.iterrows():
            kilo_house = pop_round_short(shelrow['Households'])
            kilo_disp = pop_round_short(shelrow['DisplHouse'])
            kilo_shelter = pop_round_short(shelrow['Shelter'])
            tpl = (shelrow['CountyName'],shelrow['State'],
                   kilo_house, kilo_disp, kilo_shelter)
            fmt = '%s & %s & %s & %s & %s \\\\' + '\n'
            row = fmt % tpl
            tabledata = tabledata + row

        house_total = pop_round_short(totals['Households'])
        disp_total = pop_round_short(totals['DisplHouse'])
        shelter_total = pop_round_short(totals['Shelter'])
        
        fmt = '\\textbf{Total} & & \\textbf{%s} & \\textbf{%s} & \\textbf{%s} \\\\'
        tpl =  (house_total,disp_total,shelter_total)
        row = fmt % tpl
        tabledata = tabledata + row
        return tabledata

    def getDebrisTable(self):
        deb_table, totals = self.getDebris()
        tabledata = ""
        for idx,debrow in deb_table.iterrows():
            tpl = (debrow['category'],debrow['megatons'])
            fmt = '%s & %.2f \\\\' + '\n'
            row = fmt % tpl
            tabledata = tabledata + row

        fmt = '\\textbf{Total} & \\textbf{%.2f} \\\\' + '\n'
        row =  fmt % (totals['megatons'])
        tabledata = tabledata + row

        row = ' &  \\\\' + '\n' # empty row
        tabledata = tabledata + row*2

        truck_str = commify(int(np.round(totals['truckloads'])))
        fmt = '\\textbf{Truck Loads} (@%i tons/truck)& \\textbf{%s} \\\\' + '\n'
        row = fmt % (TONS_PER_TRUCK,truck_str)
        tabledata = tabledata + row

        row = ' & (@%i tons/truck)\\\\'
        tabledata = tabledata + row
        return tabledata

    def getComment(self):
        injury_table = self.getInjuries()
        shelter_table = self.getShelterNeeds()
        loss_table = self.getLosses()
        comment_str = _get_comment_str(loss_table, injury_table,
                                       shelter_table, self._ncounties)
        return comment_str
        

def _get_comment_str(loss_table, injury_table, shelter_table,
                     total_pop, numcounties):
    comment_str = '''Expected losses estimated by Hazus include [HURT]
non-fatal injuries, approximately $[LOSS][UNITS] in direct economic losses, and 
[SHELTER] shelter needs. Impact estimates presented below represent the total 
losses calculated for the [COUNTIES] counties nearest to the earthquake epicenter
and are based on [CENSUS] census data.
'''
    injuries = injury_table['NonFatal5p'].sum()
    if injuries < INJURIES['FEW']:
        injured = 'a few'
    elif injuries >= INJURIES['FEW'] and injuries < INJURIES['SEVERAL']:
        injured = 'several'
    elif injuries >= INJURIES['SEVERAL'] and injuries < INJURIES['DOZENS']:
        injured = 'dozens of'
    elif injuries >= INJURIES['DOZENS'] and injuries < INJURIES['HUNDREDS']:
        injured = 'hundreds of'
    else:
        injured = 'thousands of'


    shelter = shelter_table['Shelter'].sum()
    shelter_fraction = shelter/total_pop
    if shelter_fraction < SHELTER['MINIMAL']:
        sheltered = 'minimal'
    elif shelter_fraction >= SHELTER['MINIMAL'] and \
         shelter_fraction < SHELTER['CONSIDERABLE']:
        sheltered = 'considerable'
    else:
        sheltered = 'extensive'

    loss, units = get_loss_string(loss_table['EconLoss'].sum())

    comment_str = comment_str.replace('[HURT]',injured)
    comment_str = comment_str.replace('[LOSS]',loss)
    comment_str = comment_str.replace('[UNITS]',units)
    comment_str = comment_str.replace('[SHELTER]',sheltered)
    comment_str = comment_str.replace('[COUNTIES]',str(numcounties))
    comment_str = comment_str.replace('[CENSUS]',CENSUS_YEAR)

    return comment_str

def get_loss_string(econloss):
    order = int(np.log10(econloss))
    if order < 3:
        units = ''
    elif order >= 3 and order < 6:
        units = 'K'
    elif order >= 6 and order < 9:
        units = 'M'
    elif order >= 9 and order < 12:
        units = 'B'
    else:
        units = 'T'
        
    if order < 3:
        number = '%3i' % (np.round(econloss))
    elif order % 3 == 0:
        fraction = econloss/np.power(10,order)
        number = '%2.1f' % (np.around(fraction,1))
    elif order % 3 == 1:
        fraction = econloss/np.power(10,order-1)
        number = '%2i' % (np.round(fraction))
    elif order % 3 == 2:
        fraction = econloss/np.power(10,order-2)
        number = '%3i' % (np.round(fraction))

    number = number.strip()
    return (number,units)
    
def get_column_tags(df):
    yellow = df['Extensive'].sum()
    red = df['Complete'].sum()
    total = df['NoDamage'].sum()
    total += df['Slight'].sum()
    total += df['Moderate'].sum()
    total += df['Extensive'].sum()
    total += df['Complete'].sum()
    total = int(total)
    return (yellow,red,total)

def _plot_tagging(heights,filename):
    heights = sorted(heights, key=lambda height: height[1])
    labels = ['%s\n(%s)' % (height[0],pop_round_short(height[3])) for height in heights]
    yellows = [height[1] for height in heights]
    reds = [height[1]+height[2] for height in heights]

    y_pos = np.arange(len(heights))

    fig = plt.figure(figsize=(6,4))
    plt.barh(y_pos,reds,color='red',edgecolor='k')
    plt.barh(y_pos,yellows,color='yellow',edgecolor='k')
    ax = plt.gca()
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels,horizontalalignment='right')

    # define the transformation from display units (pixels) to
    # data units
    inv = ax.transData.inverted()
    offset = inv.transform((RED_TAG_OFFSET,0))[0] - inv.transform((0,0))[0]

    # draw the numbers on the bar chart
    ic = 0
    for height in heights:
        yellow = int(height[1])
        red = int(height[2])
        yellow_x = yellow/2
        red_x = yellow+red + offset
        if yellow < 30:
            yellow_x = yellow + offset
            red_x = yellow_x + offset
        plt.text(yellow_x,ic,str(yellow),
                 horizontalalignment='center',
                 verticalalignment='center')
        plt.text(red_x,ic,str(red),
                 horizontalalignment='center',
                 verticalalignment='center')
        ic += 1

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.tick_params(axis='x',          # changes apply to the x-axis
                    which='both',      # both major and minor ticks are affected
                    bottom='off',      # ticks along the bottom edge are off
                    top='off',         # ticks along the top edge are off
                    labelbottom='off') # labels along the bottom edge are off
    plt.tick_params(axis='y',          # changes apply to the x-axis
                    which='both',      # both major and minor ticks are affected
                    left='off',      # ticks along the bottom edge are off
                    right='off',         # ticks along the top edge are off
                    ) # labels along the bottom edge are off

    plt.savefig(filename)

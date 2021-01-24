# stdlib imports

# third party imports
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as path_effects

import cartopy.crs as ccrs  # projections
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.feature import ShapelyFeature
import cartopy.feature as cfeature
from cartopy.io.shapereader import Reader

from mapio.reader import read
from mapio.grid2d import Grid2D

from shapely.geometry import shape as sShape
from shapely.geometry import Polygon as sPolygon
from shapely.geometry import GeometryCollection

import pyproj

import fiona

from scipy.ndimage import gaussian_filter

from impactutils.mapping.mercatormap import MercatorMap
from impactutils.mapping.city import Cities
from impactutils.colors.cpalette import ColorPalette
from impactutils.textformat.text import round_to_nearest
from impactutils.mapping.scalebar import draw_scale


# define some constants
WATERCOLOR = '#7AA1DA'
FIGWIDTH = 7.0
FILTER_SMOOTH = 5.0
XOFFSET = 4  # how many pixels between the city dot and the city text

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

# default font for cities
# DEFAULT_FONT = 'DejaVu Sans'
DEFAULT_FONT = 'Bitstream Vera Sans'

# define dictionary of MMI integer values to Roman numeral equivalents
MMI_LABELS = {'1': 'I',
              '2': 'II',
              '3': 'III',
              '4': 'IV',
              '5': 'V',
              '6': 'VI',
              '7': 'VII',
              '8': 'VIII',
              '9': 'IX',
              '10': 'X'}

DEG2KM = 111.191


def _clip_bounds(bbox, filename):
    """Clip input fiona-compatible vector file to input bounding box.

    :param bbox:
      Tuple of (xmin,ymin,xmax,ymax) desired clipping bounds.
    :param filename:
      Input name of file containing vector data in a format compatible
      with fiona.
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


def _renderRow(row, ax, fontname=DEFAULT_FONT, fontsize=10, zorder=10,
               shadow=False):
    """Internal method to consistently render city names.
    :param row:
      pandas dataframe row.
    :param ax:
      Matplotlib Axes instance.
    :param fontname:
      String name of desired font.
    :param fontsize:
      Font size in points.
    :param zorder:
      Matplotlib plotting order - higher zorder is on top.
    :param shadow:
      Boolean indicating whether "drop-shadow" effect should be used.
    :returns:
      Matplotlib Text instance.
    """
    ha = 'left'
    va = 'center'
    if 'placement' in row.index:
        if row['placement'].find('E') > -1:
            ha = 'left'
        if row['placement'].find('W') > -1:
            ha = 'right'
        else:
            ha = 'center'
        if row['placement'].find('N') > -1:
            ha = 'top'
        if row['placement'].find('S') > -1:
            ha = 'bottom'
        else:
            ha = 'center'

    data_x_offset = 0
    tx = row['lon'] + data_x_offset
    ty = row['lat']
    if shadow:
        th = ax.text(tx, ty, row['name'], fontname=fontname, color='black',
                     fontsize=fontsize, ha=ha, va=va, zorder=zorder,
                     transform=ccrs.Geodetic())
        th.set_path_effects([path_effects.Stroke(linewidth=2.0,
                                                 foreground='white'),
                             path_effects.Normal()])
    else:
        th = ax.text(tx, ty, row['name'], fontname=fontname,
                     fontsize=fontsize, ha=ha, va=va, zorder=zorder,
                     transform=ccrs.Geodetic())

    return th


def _get_open_corner(popgrid, ax, filled_corner=None, need_bottom=True):
    """Get the map corner (not already filled) with the lowest population.

    :param popgrid:
      Grid2D object containing population data.
    :param ax:
      Axes object filled by input population grid.
    :param filled_corner:
      String indicating which, if any, corners are already occupied.
      One of ('ll','lr','ul','ur').
    :param need_bottom:
      Boolean indicating that one of the two lower corners should be preferred.
    :returns:
      Tuple of:
         - Tuple of corner values in figure coordinates, used to place new
           axes in a figure.
        (left,bottom,width,height)
         - String indicating which corner was selected.
    """
    # define all edges in AXES coordinates, then convert to figure coordinates.
    ax_width = 0.14
    ax_height = 0.14
    ax_gap = 0.01
    ax_leftleft = ax_gap
    ax_rightleft = 1.0 - (ax_gap + ax_width)
    ax_bottombottom = ax_gap
    ax_topbottom = 1.0 - (ax_gap + ax_width)

    axes2disp = ax.transAxes
    disp2fig = ax.figure.transFigure.inverted()
    # ll
    leftleft, bottombottom = disp2fig.transform(
        axes2disp.transform((ax_leftleft, ax_bottombottom)))
    # lr
    rightleft, bottombottom = disp2fig.transform(
        axes2disp.transform((ax_rightleft, ax_bottombottom)))
    # ur
    rightleft, topbottom = disp2fig.transform(
        axes2disp.transform((ax_rightleft, ax_topbottom)))
    # right edge of the left bottom corner rectangle
    leftright, bottombottom = disp2fig.transform(
        axes2disp.transform((ax_leftleft + ax_width, ax_bottombottom)))
    leftleft, bottomtop = disp2fig.transform(
        axes2disp.transform((ax_leftleft, ax_bottombottom + ax_height)))
    width = leftright - leftleft
    height = bottomtop - bottombottom

    # get info about population grid
    popdata = popgrid.getData().copy()
    i = np.where(np.isnan(popdata))
    popdata[i] = 0
    nrows, ncols = popdata.shape

    ulpopsum = popdata[0:int(nrows / 4), 0:int(ncols / 4)].sum()
    ulbounds = (leftleft, topbottom, width, height)

    urpopsum = popdata[0:int(nrows / 4), ncols -
                       int(ncols / 4):ncols - 1].sum()
    urbounds = (rightleft, topbottom, width, height)

    llpopsum = popdata[nrows - int(nrows / 4)
                                   :nrows - 1, 0:int(ncols / 4)].sum()
    llbounds = (leftleft, bottombottom, width, height)

    lrpopsum = popdata[nrows - int(nrows / 4):nrows - 1,
                       ncols - int(ncols / 4):ncols - 1].sum()
    lrbounds = (rightleft, bottombottom, width, height)

    if filled_corner == 'll' and need_bottom:
        return lrbounds, 'lr'

    if filled_corner == 'lr' and need_bottom:
        return llbounds, 'll'

    # get the index of the already filled corner
    if filled_corner is not None:
        corners = ['ll', 'lr', 'ul', 'ur']
        cidx = corners.index(filled_corner)
    else:
        cidx = None

    # get the population sums in each of the four corners
    allsums = np.array([llpopsum, lrpopsum, ulpopsum, urpopsum])
    isort = allsums.argsort()

    if need_bottom:
        i = np.where(isort <= 1)[0]
        isort = isort[i]
    if cidx is not None:
        i = np.where(isort != cidx)[0]
        isort = isort[i]

    imin = isort[0]

    if imin == 0:
        return llbounds, 'll'
    if imin == 1:
        return lrbounds, 'lr'
    if imin == 2:
        return ulbounds, 'ul'
    if imin == 3:
        return urbounds, 'ur'


def draw_contour(shakegrid, popgrid, oceanfile, oceangridfile, cityfile,
                 basename, borderfile=None, is_scenario=False):
    """Create a contour map showing MMI contours over greyscale population.

    :param shakegrid:
      ShakeGrid object.
    :param popgrid:
      Grid2D object containing population data.
    :param oceanfile:
      String path to file containing ocean vector data in a format compatible
      with fiona.
    :param oceangridfile:
      String path to file containing ocean grid data .
    :param cityfile:
      String path to file containing GeoNames cities data.
    :param basename:
      String path containing desired output PDF base name, i.e.,
      /home/pager/exposure.  ".pdf" and ".png" files will
      be made.
    :param make_png:
      Boolean indicating whether a PNG version of the file should also be
      created in the same output folder as the PDF.
    :returns:
      Tuple containing:
        - Name of PNG file created, or None if PNG output not specified.
        - Cities object containing the cities that were rendered on the
          contour map.
    """
    gd = shakegrid.getGeoDict()

    # Retrieve the epicenter - this will get used on the map
    center_lat = shakegrid.getEventDict()['lat']
    center_lon = shakegrid.getEventDict()['lon']

    # load the ocean grid file (has 1s in ocean, 0s over land)
    # having this file saves us almost 30 seconds!
    oceangrid = read(oceangridfile,
                     samplegeodict=gd,
                     resample=True,
                     doPadding=True)

    # load the cities data, limit to cities within shakemap bounds
    allcities = Cities.fromDefault()
    cities = allcities.limitByBounds((gd.xmin, gd.xmax, gd.ymin, gd.ymax))

    # define the map
    # first cope with stupid 180 meridian
    height = (gd.ymax - gd.ymin) * DEG2KM
    if gd.xmin < gd.xmax:
        width = (gd.xmax - gd.xmin) * np.cos(np.radians(center_lat)) * DEG2KM
        xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
    else:
        xmin, xmax, ymin, ymax = (gd.xmin, gd.xmax, gd.ymin, gd.ymax)
        xmax += 360
        width = ((gd.xmax + 360) - gd.xmin) * \
            np.cos(np.radians(center_lat)) * DEG2KM

    aspect = width / height

    # if the aspect is not 1, then trim bounds in x or y direction
    # as appropriate
    if width > height:
        dw = (width - height) / 2.0  # this is width in km
        xmin = xmin + dw / (np.cos(np.radians(center_lat)) * DEG2KM)
        xmax = xmax - dw / (np.cos(np.radians(center_lat)) * DEG2KM)
        width = (xmax - xmin) * np.cos(np.radians(center_lat)) * DEG2KM
    if height > width:
        dh = (height - width) / 2.0  # this is width in km
        ymin = ymin + dh / DEG2KM
        ymax = ymax - dh / DEG2KM
        height = (ymax - ymin) * DEG2KM

    aspect = width / height
    figheight = FIGWIDTH / aspect
    bbox = (xmin, ymin, xmax, ymax)
    bounds = (xmin, xmax, ymin, ymax)
    figsize = (FIGWIDTH, figheight)

    # Create the MercatorMap object, which holds a separate but identical
    # axes object used to determine collisions between city labels.
    mmap = MercatorMap(bounds, figsize, cities, padding=0.5)
    fig = mmap.figure
    ax = mmap.axes
    # this needs to be done here so that city label collision
    # detection will work
    fig.canvas.draw()

    geoproj = mmap.geoproj
    proj = mmap.proj

    # project our population grid to the map projection
    projstr = proj.proj4_init
    popgrid_proj = popgrid.project(projstr)
    popdata = popgrid_proj.getData()
    newgd = popgrid_proj.getGeoDict()

    # Use our GMT-inspired palette class to create population and MMI colormaps
    popmap = ColorPalette.fromPreset('pop')
    mmimap = ColorPalette.fromPreset('mmi')

    # set the image extent to that of the data
    img_extent = (newgd.xmin, newgd.xmax, newgd.ymin, newgd.ymax)
    plt.imshow(popdata, origin='upper', extent=img_extent, cmap=popmap.cmap,
               vmin=popmap.vmin, vmax=popmap.vmax, zorder=POP_ZORDER,
               interpolation='nearest')

    # draw 10m res coastlines
    ax.coastlines(resolution="10m", zorder=COAST_ZORDER)

    states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none')

    ax.add_feature(states_provinces, edgecolor='black', zorder=COAST_ZORDER)

    # draw country borders using natural earth data set
    if borderfile is not None:
        borders = ShapelyFeature(Reader(borderfile).geometries(),
                                 ccrs.PlateCarree())
        ax.add_feature(borders, zorder=COAST_ZORDER,
                       edgecolor='black', linewidth=2, facecolor='none')

    # clip the ocean data to the shakemap
    bbox = (gd.xmin, gd.ymin, gd.xmax, gd.ymax)
    oceanshapes = _clip_bounds(bbox, oceanfile)

    ax.add_feature(ShapelyFeature(oceanshapes, crs=geoproj),
                   facecolor=WATERCOLOR, zorder=OCEAN_ZORDER)

    # So here we're going to project the MMI data to
    # our mercator map, then smooth and contour that
    # projected grid.

    # smooth the MMI data for contouring, themn project
    mmi = shakegrid.getLayer('mmi').getData()
    smoothed_mmi = gaussian_filter(mmi, FILTER_SMOOTH)
    newgd = shakegrid.getGeoDict().copy()
    smooth_grid = Grid2D(data=smoothed_mmi, geodict=newgd)
    smooth_grid_merc = smooth_grid.project(projstr)
    newgd2 = smooth_grid_merc.getGeoDict()

    # project the ocean grid
    oceangrid_merc = oceangrid.project(projstr)

    # create masked arrays using the ocean grid
    data_xmin, data_xmax = newgd2.xmin, newgd2.xmax
    data_ymin, data_ymax = newgd2.ymin, newgd2.ymax
    smooth_data = smooth_grid_merc.getData()
    landmask = np.ma.masked_where(oceangrid_merc._data == 0.0, smooth_data)
    oceanmask = np.ma.masked_where(oceangrid_merc._data == 1.0, smooth_data)

    # contour the data
    contourx = np.linspace(data_xmin, data_xmax, newgd2.nx)
    contoury = np.linspace(data_ymin, data_ymax, newgd2.ny)
    ax.contour(contourx, contoury, np.flipud(oceanmask),
               linewidths=3.0, linestyles='solid',
               zorder=1000, cmap=mmimap.cmap,
               vmin=mmimap.vmin, vmax=mmimap.vmax,
               levels=np.arange(0.5, 10.5, 1.0),
               )

    ax.contour(contourx, contoury, np.flipud(landmask),
               linewidths=2.0, linestyles='dashed',
               zorder=OCEANC_ZORDER, cmap=mmimap.cmap,
               vmin=mmimap.vmin, vmax=mmimap.vmax,
               levels=np.arange(0.5, 10.5, 1.0),
               )

    # the idea here is to plot invisible MMI contours at integer levels
    # and then label them. clabel method won't allow text to appear,
    # which is this case is kind of ok, because it allows us an
    # easy way to draw MMI labels as roman numerals.
    cs_land = plt.contour(contourx, contoury, np.flipud(oceanmask),
                          linewidths=0.0, levels=np.arange(0, 11), alpha=0.0,
                          zorder=CLABEL_ZORDER, )

    roman_format_dict = {1: 'I',
                         2: 'II',
                         3: 'III',
                         4: 'IV',
                         5: 'V',
                         6: 'VI',
                         7: 'VII',
                         8: 'VIII',
                         9: 'IX',
                         10: 'X',
                         }
    clabel_text_land = ax.clabel(cs_land, cs_land.cvalues,
                                 colors='k', fmt=roman_format_dict,
                                 fontsize=16, zorder=CLABEL_ZORDER)
    # this sometimes works to draw a shadow effect, but other times
    # results in a duplicate offset roman numeral all in white.
    # TODO: Figure this out!+
    # for clabel in clabel_text_land:
    #     clabel.set_path_effects([path_effects.Stroke(linewidth=2.0,
    #                                                  foreground='white'),
    #                              path_effects.Normal()])

    cs_ocean = plt.contour(contourx, contoury, np.flipud(landmask),
                           linewidths=0.0, levels=np.arange(0, 11),
                           zorder=CLABEL_ZORDER, )

    clabel_text_ocean = ax.clabel(cs_ocean, cs_ocean.cvalues, colors='k',
                                  fmt=roman_format_dict, fontsize=16,
                                  zorder=CLABEL_ZORDER)
    # this sometimes works to draw a shadow effect, but other times
    # results in a duplicate offset roman numeral all in white.
    # TODO: Figure this out!
    # for clabel in clabel_text:
    #     clabel.set_path_effects([path_effects.Stroke(linewidth=2.0,
    #                                                  foreground='white'),
    #                              path_effects.Normal()])

    # draw meridians and parallels using Cartopy's functions for that
    gl = ax.gridlines(draw_labels=True,
                      linewidth=2, color=(0.9, 0.9, 0.9),
                      alpha=0.5, linestyle='-',
                      zorder=GRID_ZORDER)
    gl.xlabels_top = False
    gl.xlabels_bottom = False
    gl.ylabels_left = False
    gl.ylabels_right = False
    gl.xlines = True

    # let's floor/ceil the edges to nearest half a degree
    gxmin = np.floor(xmin * 2) / 2
    gxmax = np.ceil(xmax * 2) / 2
    gymin = np.floor(ymin * 2) / 2
    gymax = np.ceil(ymax * 2) / 2

    xlocs = np.linspace(gxmin, gxmax + 0.5, num=5)
    ylocs = np.linspace(gymin, gymax + 0.5, num=5)

    gl.xlocator = mticker.FixedLocator(xlocs)
    gl.ylocator = mticker.FixedLocator(ylocs)
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {'size': 15, 'color': 'black'}
    gl.ylabel_style = {'size': 15, 'color': 'black'}

    # TODO - figure out x/y axes data coordinates
    # corresponding to 10% from left and 10% from top
    # use geoproj and proj
    dleft = 0.01
    dtop = 0.97
    proj_str = proj.proj4_init
    merc_to_dd = pyproj.Proj(proj_str)

    # use built-in transforms to get from axes units to data units
    display_to_data = ax.transData.inverted()
    axes_to_display = ax.transAxes

    # these are x,y coordinates in projected space
    yleft, t1 = display_to_data.transform(
        axes_to_display.transform((dleft, 0.5)))
    t2, xtop = display_to_data.transform(
        axes_to_display.transform((0.5, dtop)))

    # these are coordinates in lon,lat space
    yleft_dd, t1_dd = merc_to_dd(yleft, t1, inverse=True)
    t2_dd, xtop_dd = merc_to_dd(t2, xtop, inverse=True)

    # drawing our own tick labels INSIDE the plot, as
    # Cartopy doesn't seem to support this.
    yrange = ymax - ymin
    xrange = xmax - xmin
    ddlabelsize = 12
    for xloc in gl.xlocator.locs:
        outside = xloc < xmin or xloc > xmax
        # don't draw labels when we're too close to either edge
        near_edge = (xloc - xmin) < (xrange *
                                     0.1) or (xmax - xloc) < (xrange * 0.1)
        if outside or near_edge:
            continue
        direction = 'W'
        if xloc >= 0:
            direction = 'E'
        xtext = r'$%.1f^\circ$%s' % (abs(xloc), direction)
        ax.text(xloc, xtop_dd, xtext,
                fontsize=ddlabelsize, zorder=GRID_ZORDER, ha='center',
                fontname=DEFAULT_FONT,
                transform=ccrs.Geodetic())

    for yloc in gl.ylocator.locs:
        outside = yloc < gd.ymin or yloc > gd.ymax
        # don't draw labels when we're too close to either edge
        near_edge = (yloc - gd.ymin) < (yrange *
                                        0.1) or (gd.ymax - yloc) < (yrange * 0.1)
        if outside or near_edge:
            continue
        if yloc < 0:
            ytext = r'$%.1f^\circ$S' % (abs(yloc))
        else:
            ytext = r'$%.1f^\circ$N' % (abs(yloc))
        ax.text(yleft_dd, yloc, ytext,
                fontsize=ddlabelsize, zorder=GRID_ZORDER, va='center',
                fontname=DEFAULT_FONT,
                transform=ccrs.Geodetic())

    # draw cities
    mapcities = mmap.drawCities(shadow=True, zorder=CITIES_ZORDER)

    # draw the figure border thickly
    # TODO - figure out how to draw map border
    # bwidth = 3
    # ax.spines['top'].set_visible(True)
    # ax.spines['left'].set_visible(True)
    # ax.spines['bottom'].set_visible(True)
    # ax.spines['right'].set_visible(True)
    # ax.spines['top'].set_linewidth(bwidth)
    # ax.spines['right'].set_linewidth(bwidth)
    # ax.spines['bottom'].set_linewidth(bwidth)
    # ax.spines['left'].set_linewidth(bwidth)

    # Get the corner of the map with the lowest population
    corner_rect, filled_corner = _get_open_corner(popgrid, ax)
    clat2 = round_to_nearest(center_lat, 1.0)
    clon2 = round_to_nearest(center_lon, 1.0)

    # draw a little globe in the corner showing in small-scale
    # where the earthquake is located.
    proj = ccrs.Orthographic(central_latitude=clat2,
                             central_longitude=clon2)
    ax2 = fig.add_axes(corner_rect, projection=proj)
    ax2.add_feature(cfeature.OCEAN, zorder=0,
                    facecolor=WATERCOLOR, edgecolor=WATERCOLOR)
    ax2.add_feature(cfeature.LAND, zorder=0, edgecolor='black')
    ax2.plot([clon2], [clat2], 'w*', linewidth=1, markersize=16,
             markeredgecolor='k', markerfacecolor='r')
    ax2.gridlines()
    ax2.set_global()
    ax2.outline_patch.set_edgecolor('black')
    ax2.outline_patch.set_linewidth(2)

    # Draw the map scale in the unoccupied lower corner.
    corner = 'lr'
    if filled_corner == 'lr':
        corner = 'll'
    draw_scale(ax, corner, pady=0.05, padx=0.05)

    # Draw the epicenter as a black star
    plt.sca(ax)
    plt.plot(center_lon, center_lat, 'k*', markersize=16,
             zorder=EPICENTER_ZORDER, transform=geoproj)

    if is_scenario:
        plt.text(center_lon, center_lat, 'SCENARIO', fontsize=64,
                 zorder=WATERMARK_ZORDER, transform=geoproj,
                 alpha=0.2, color='red', horizontalalignment='center')

    # create pdf and png output file names
    pdf_file = basename + '.pdf'
    png_file = basename + '.png'

    # save to pdf
    plt.savefig(pdf_file)
    plt.savefig(png_file)

    return (pdf_file, png_file, mapcities)

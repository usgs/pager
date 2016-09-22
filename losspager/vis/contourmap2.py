#stdlib imports
import os.path
from datetime import datetime

#third party imports
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import cartopy
import cartopy.crs as ccrs  # projections
import cartopy.feature as cfeature   # features such as coast 
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.io.img_tiles import StamenTerrain  # baselayer map

from mapio.shake import ShakeGrid
from mapio.gdal import GDALGrid
from mapio.grid2d import Grid2D

from shapely.geometry import shape as sShape
from shapely.geometry import Polygon as sPolygon
from shapely.geometry import MultiPolygon as mPolygon

import fiona

from descartes import PolygonPatch
from scipy.ndimage import gaussian_filter

from impactutils.mapping.cartopycity import CartopyCities
from impactutils.colors.cpalette import ColorPalette
from impactutils.textformat.text import round_to_nearest
from impactutils.mapping.scalebar import draw_scale

#define some constants
WATERCOLOR = '#7AA1DA'
FIGWIDTH = 7.0
FILTER_SMOOTH = 5.0

def _clip_bounds(bbox,filename):
    """Clip input fiona-compatible vector file to input bounding box.

    :param bbox:
      Tuple of (xmin,ymin,xmax,ymax) desired clipping bounds.
    :param filename:
      Input name of file containing vector data in a format compatible with fiona.
    :returns:
      Shapely Geometry object (Polygon or MultiPolygon).
    """
    #returns a clipped shapely object
    xmin,ymin,xmax,ymax = bbox
    bboxpoly = sPolygon([(xmin,ymax),(xmax,ymax),(xmax,ymin),(xmin,ymin),(xmin,ymax)])
    vshapes = []
    f = fiona.open(filename,'r')
    shapes = f.items(bbox=bbox)
    for shapeidx,shape in shapes:
        tshape = sShape(shape['geometry'])
        intshape = tshape.intersection(bboxpoly)
        vshapes.append(intshape)
    f.close()
    return vshapes

def _get_open_corner(popgrid,ax,filled_corner=None,need_bottom=True):
    """Get the map corner (not already filled) with the lowest population.

    :param popgrid:
      Grid2D object containing population data.
    :param ax:
      Axes object filled by input population grid.
    :param filled_corner:
      String indicating which, if any, corners are already occupied. One of ('ll','lr','ul','ur').
    :param need_bottom:
      Boolean indicating that one of the two lower corners should be preferred.
    :returns:
      Tuple of:
         - Tuple of corner values in figure coordinates, used to place new axes in a figure. 
        (left,bottom,width,height)
         - String indicating which corner was selected.
    """
    #define all edges in AXES coordinates, then convert to figure coordinates.
    ax_width = 0.14
    ax_height = 0.14
    ax_gap = 0.01
    ax_leftleft = ax_gap
    ax_rightleft = 1.0 - (ax_gap + ax_width)
    ax_bottombottom = ax_gap
    ax_topbottom = 1.0 - (ax_gap + ax_width)
    

    axes2disp = ax.transAxes
    disp2fig = ax.figure.transFigure.inverted()
    #ll
    leftleft,bottombottom = disp2fig.transform(axes2disp.transform((ax_leftleft,ax_bottombottom)))
    #lr
    rightleft,bottombottom = disp2fig.transform(axes2disp.transform((ax_rightleft,ax_bottombottom)))
    #ur
    rightleft,topbottom = disp2fig.transform(axes2disp.transform((ax_rightleft,ax_topbottom)))
    #right edge of the left bottom corner rectangle
    leftright,bottombottom = disp2fig.transform(axes2disp.transform((ax_leftleft+ax_width,ax_bottombottom)))
    leftleft,bottomtop = disp2fig.transform(axes2disp.transform((ax_leftleft,ax_bottombottom+ax_height)))
    width = leftright - leftleft
    height = bottomtop - bottombottom

    #get info about population grid
    popdata = popgrid.getData().copy()
    i = np.where(np.isnan(popdata))
    popdata[i] = 0
    nrows,ncols = popdata.shape

    ulpopsum = popdata[0:int(nrows/4),0:int(ncols/4)].sum()
    ulbounds = (leftleft,topbottom,width,height)
        
    urpopsum = popdata[0:int(nrows/4),ncols - int(ncols/4):ncols-1].sum()
    urbounds = (rightleft,topbottom,width,height)

    llpopsum = popdata[nrows - int(nrows/4):nrows-1,0:int(ncols/4)].sum()
    llbounds = (leftleft,bottombottom,width,height)

    lrpopsum = popdata[nrows - int(nrows/4):nrows-1,ncols - int(ncols/4):ncols-1].sum()
    lrbounds = (rightleft,bottombottom,width,height)
    
    if filled_corner == 'll' and need_bottom:
        return lrbounds,'lr'

    if filled_corner == 'lr' and need_bottom:
        return llbounds,'ll'

    #get the index of the already filled corner
    if filled_corner is not None:
        corners = ['ll','lr','ul','ur']
        cidx = corners.index(filled_corner)
    else:
        cidx = None

    #get the population sums in each of the four corners
    allsums = np.array([llpopsum,lrpopsum,ulpopsum,urpopsum])
    isort = allsums.argsort()
    
    if need_bottom:
        i = np.where(isort <= 1)[0]
        isort = isort[i]
    if cidx is not None:
        i = np.where(isort != cidx)[0]
        isort = isort[i]

    imin = isort[0]

    if imin == 0:
        return llbounds,'ll'
    if imin == 1:
        return lrbounds,'lr'
    if imin == 2:
        return ulbounds,'ul'
    if imin == 3:
        return urbounds,'ur'


def draw_contour(shakefile,popfile,oceanfile,cityfile,outfilename,make_png=False):
    """Create a contour map showing population (greyscale) underneath contoured MMI.

    :param shakefile:
      String path to ShakeMap grid.xml file.
    :param popfile:
      String path to GDALGrid-compliant file containing population data.
    :param oceanfile:
      String path to file containing ocean vector data in a format compatible with fiona.
    :param cityfile:
      String path to file containing GeoNames cities data.
    :param outfilename:
      String path containing desired output PDF filename.
    :param make_png:
      Boolean indicating whether a PNG version of the file should also be created in the
      same output folder as the PDF.
    :returns:
      Name of PNG file created, or None if PNG output not specified.
    """
    #load the shakemap - for the time being, we're interpolating the 
    #population data to the shakemap, which would be important
    #if we were doing math with the pop values.  We're not, so I think it's ok.
    shakegrid = ShakeGrid.load(shakefile,adjust='res')
    gd = shakegrid.getGeoDict()
    
    #retrieve the epicenter - this will get used on the map
    clat = shakegrid.getEventDict()['lat']
    clon = shakegrid.getEventDict()['lon']

    #load the population data, sample to shakemap
    popgrid = GDALGrid.load(popfile,samplegeodict=gd,resample=True)
    popdata = popgrid.getData()
    
    #smooth the MMI data for contouring
    mmi = shakegrid.getLayer('mmi').getData()
    smoothed_mmi = gaussian_filter(mmi,FILTER_SMOOTH)

    #clip the ocean data to the shakemap
    bbox = (gd.xmin,gd.ymin,gd.xmax,gd.ymax)
    oceanshapes = _clip_bounds(bbox,oceanfile)

    #load the cities data, limit to cities within shakemap bounds
    allcities = CartopyCities.fromDefault()
    cities = allcities.limitByBounds((gd.xmin,gd.xmax,gd.ymin,gd.ymax))

    # Define ocean/land masks to do the contours, since we want different contour line styles over land and water.
    oceangrid = Grid2D.rasterizeFromGeometry(oceanshapes,gd,burnValue=1.0,fillValue=0.0,
                                             mustContainCenter=False,attribute=None)
    oceanmask = np.ma.masked_where(oceangrid == 1.0,smoothed_mmi)
    landmask = np.ma.masked_where(oceangrid == 0.0,smoothed_mmi)

    # Use our GMT-inspired palette class to create population and MMI colormaps 
    popmap = ColorPalette.fromPreset('pop')
    mmimap = ColorPalette.fromPreset('mmi')

    #use the ShakeMap to determine the aspect ratio of the map
    aspect = (gd.xmax-gd.xmin)/(gd.ymax-gd.ymin)
    figheight = FIGWIDTH/aspect
    fig = plt.figure(figsize=(FIGWIDTH,figheight))

    # set up axes object with PlateCaree (non) projection.
    ax = plt.axes([0.02,0.02,0.95,0.95],projection=ccrs.PlateCarree())

    #set the image extent to that of the data
    img_extent = (gd.xmin,gd.xmax,gd.ymin,gd.ymax)
    plt.imshow(popdata,origin='upper',extent=img_extent,cmap=popmap.cmap,
               vmin=popmap.vmin,vmax=popmap.vmax,zorder=9,interpolation='none')

    #define arrays of latitude and longitude we will use to plot MMI contours
    lat = np.linspace(gd.ymin,gd.ymax,gd.ny)
    lon = np.linspace(gd.xmin,gd.xmax,gd.nx)

    #contour the masked land/ocean MMI data at half-integer levels
    plt.contour(lon,lat,landmask,linewidths=3.0,linestyles='solid',zorder=10,
                cmap=mmimap.cmap,vmin=mmimap.vmin,vmax=mmimap.vmax,
                levels=np.arange(0.5,10.5,1.0))

    plt.contour(lon,lat,oceanmask,linewidths=2.0,linestyles='dashed',zorder=13,
                cmap=mmimap.cmap,vmin=mmimap.vmin,vmax=mmimap.vmax,
                levels=np.arange(0.5,10.5,1.0))


    #the idea here is to plot invisible MMI contours at integer levels and then label them.
    #labeling part does not currently work.
    cs=plt.contour(lon,lat,landmask,linewidths=0.0,levels=np.arange(0,11),zorder=10)
    #clabel is not actually drawing anything, but it is blotting out a portion of the contour line.  ??
    ax.clabel(cs,np.arange(0,11),colors='k',zorder=25)

    #set the extent of the map to our data
    ax.set_extent([lon.min(), lon.max(), lat.min(), lat.max()])

    #draw the ocean data
    if isinstance(oceanshapes[0],mPolygon):
        for shape in oceanshapes[0]:
            ocean_patch = PolygonPatch(shape,zorder=10,facecolor=WATERCOLOR,edgecolor=WATERCOLOR)
            ax.add_patch(ocean_patch);
    else:
        ocean_patch = PolygonPatch(oceanshapes[0],zorder=10,facecolor=WATERCOLOR,edgecolor=WATERCOLOR)
        ax.add_patch(ocean_patch);

    # add coastlines with desired scale of resolution
    ax.coastlines('10m', zorder=11);

    #draw meridians and parallels using Cartopy's functions for that
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=2, color=(0.9,0.9,0.9), alpha=0.5, linestyle='-',
                     zorder=20)
    gl.xlabels_top = False
    gl.xlabels_bottom = False
    gl.ylabels_left = False
    gl.ylabels_right = False
    gl.xlines = True
    xlocs = np.arange(np.floor(gd.xmin-1),np.ceil(gd.xmax+1))
    ylocs = np.arange(np.floor(gd.ymin-1),np.ceil(gd.ymax+1))
    gl.xlocator = mticker.FixedLocator(xlocs)
    gl.ylocator = mticker.FixedLocator(ylocs)
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {'size': 15, 'color': 'black'}
    gl.ylabel_style = {'size': 15, 'color': 'black'}

    #drawing our own tick labels INSIDE the plot, as Cartopy doesn't seem to support this.
    yrange = gd.ymax - gd.ymin
    xrange = gd.xmax - gd.xmin
    for xloc in gl.xlocator.locs:
        outside = xloc < gd.xmin or xloc > gd.xmax
        #don't draw labels when we're too close to either edge
        near_edge = (xloc-gd.xmin) < (xrange*0.1) or (gd.xmax-xloc) < (xrange*0.1)
        if outside or near_edge:
            continue
        if xloc < 0:
            xtext = r'$%s^\circ$W' % str(abs(int(xloc)))
        else:
            xtext = r'$%s^\circ$E' % str(int(xloc))
        ax.text(xloc,gd.ymax-(yrange/35),xtext,
                 fontsize=14,zorder=20,ha='center',
                fontname='Bitstream Vera Sans')

    for yloc in gl.ylocator.locs:
        outside = yloc < gd.ymin or yloc > gd.ymax
        #don't draw labels when we're too close to either edge
        near_edge = (yloc-gd.ymin) < (yrange*0.1) or (gd.ymax-yloc) < (yrange*0.1)
        if outside or near_edge:
            continue
        if yloc < 0:
            ytext = r'$%s^\circ$S' % str(abs(int(yloc)))
        else:
            ytext = r'$%s^\circ$N' % str(int(yloc))
        thing = ax.text(gd.xmin+(xrange/100),yloc,ytext,
                     fontsize=14,zorder=20,va='center',
                    fontname='Bitstream Vera Sans')

    #Limit the number of cities we show - we may not want to use the population size
    #filter in the global case, but the map collision filter is a little sketchy right now.
    mapcities = cities.limitByPopulation(25000)
    mapcities = mapcities.limitByGrid()
    mapcities = mapcities.limitByMapCollision(ax,shadow=True)
    mapcities.renderToMap(ax,shadow=True,fontsize=12,zorder=11)

    #Get the corner of the map with the lowest population
    corner_rect,filled_corner = _get_open_corner(popgrid,ax)
    clat = round_to_nearest(clat,1.0)
    clon = round_to_nearest(clon,1.0)

    #draw a little globe in the corner showing in small-scale where the earthquake is located.
    proj = ccrs.Orthographic(central_latitude=clat,
                            central_longitude=clon)
    ax2 = fig.add_axes(corner_rect,projection=proj)
    ax2.add_feature(cartopy.feature.OCEAN, zorder=0,facecolor=WATERCOLOR,edgecolor=WATERCOLOR)
    ax2.add_feature(cartopy.feature.LAND, zorder=0, edgecolor='black')
    ax2.plot([clon],[clat],'w*',linewidth=1,markersize=16,markeredgecolor='k',markerfacecolor='r')
    gh=ax2.gridlines();
    ax2.set_global();
    ax2.outline_patch.set_edgecolor('black')
    ax2.outline_patch.set_linewidth(2);

    #Draw the map scale in the unoccupied lower corner.
    corner = 'lr'
    if filled_corner == 'lr':
        corner = 'll'
    draw_scale(ax,corner,pady=0.05,padx=0.05)
    
    plt.savefig(outfilename)

    pngfile = None
    if make_png:
        fpath,fname = os.path.split(outfilename)
        fbase,t = os.path.splitext(fname)
        pngfile = os.path.join(fpath,fbase+'.png')
        plt.savefig(pngfile)
    
    return pngfile


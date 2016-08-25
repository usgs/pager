#!/usr/bin/env python

#stdlib
import os.path
import time
from functools import partial
from collections import OrderedDict

#third party
from mapio.basemapcity import BasemapCities
from mapio.gmt import GMTGrid
import fiona
from matplotlib.patches import Polygon
from matplotlib.colors import LightSource,LinearSegmentedColormap,BoundaryNorm
import matplotlib.pyplot as plt
from shapely.ops import transform
from shapely.geometry import MultiPolygon
from shapely.geometry import MultiLineString
from shapely.geometry import GeometryCollection
from shapely.geometry import Polygon as sPolygon
from shapely.geometry import LineString
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.collection import GeometryCollection
from shapely.geometry import shape as sShape
from shapely.geometry import mapping
from mpl_toolkits.basemap import Basemap
import numpy as np
from descartes import PolygonPatch
from scipy.ndimage import gaussian_filter
import pyproj
from matplotlib import _cntr as cntr

#local imports
from impactutils.textformat.text import dec_to_roman


CITY_COLS = 2
CITY_ROWS = 2
CITIES_PER_GRID = 10
FIG_WIDTH = 8
FIG_HEIGHT = 8
BASEMAP_RESOLUTION = 'c'
WATERCOLOR = '#7AA1DA'
NCONTOURS = 6
VERT_EXAG = 0.1

#all of the zorder values for different plotted parameters
IMG_ZORDER = 1
STATIONS_ZORDER = 250
CITIES_ZORDER = 100
FAULT_ZORDER = 500
EPICENTER_ZORDER = 500
CONTOUR_ZORDER = 800
ROAD_ZORDER = 5
SCALE_ZORDER = 1500
GRATICULE_ZORDER = 1200
OCEAN_ZORDER = 1000
BORDER_ZORDER = 1001
CONTOUR_ZORDER = 2000

def cosd(angle):
    return np.cos(np.radians(angle))

def sind(angle):
    return np.sin(np.radians(angle))

def gethexcolor(color):
    nlist = [int(c*255) for c in color]
    h1 = hex(nlist[0])[2:4]
    h2 = hex(nlist[1])[2:4]
    h3 = hex(nlist[2])[2:4]
    return '#%s%s%s' % (h1,h2,h3)

#http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg04050.html
class FormatFaker(object):
    def __init__(self, str): self.str = str
    def __mod__(self, stuff): return self.str

def getPopColorMap():
    zvalues = [0,0,5,50,100,500,1000,5000,10000,10000]
    greys = [255,255,203,175,145,114,80,41,0,0]
    cmap = {'red':[],
            'green':[],
            'blue':[]}

    for i in range(0,len(zvalues)-1):
        x = zvalues[i]/max(zvalues)
        y0 = greys[i]/255
        y1 = greys[i+1]/255
        cmap['red'].append((x,y0,y1))
        cmap['green'].append((x,y0,y1))
        cmap['blue'].append((x,y0,y1))
        
    cmap =  LinearSegmentedColormap('popmap',cmap)
    return cmap

def plotContourLabel(map,label):
    fontsize = 14
    fontdict1 = {'fontweight':'light',
                 'color': 'w',
                 'fontsize':fontsize}
    fontdict2 = {'fontweight':'light',
                 'color': 'k',
                 'fontsize':fontsize}
    xd = (map.urcrnrx - map.llcrnrx)/500
    yd = (map.urcrnry - map.llcrnry)/500
    ltext = label.get_text()
    lrot = label.get_rotation()
    lx,ly = label.get_position()
    va, ha = label.get_va(), label.get_ha()
    protmat = np.array([[cosd(lrot),sind(lrot)],
                        [-1*sind(lrot),cosd(lrot)]])
    nrotmat = np.linalg.pinv(protmat)
    xlist = [-1*xd,0,xd,xd,xd,0,-1*xd,-1*xd]
    ylist = [yd,yd,yd,0,-1*yd,-1*yd,-1*yd,0]
    for dx,dy in zip(xlist,ylist):
        xrot,yrot = np.dot(protmat,np.array([[lx],[ly]]))
        xrot = xrot + dx
        yrot = yrot + dy
        newx,newy = np.dot(nrotmat,np.array([[xrot[0]],[yrot[0]]]))
        plt.text(newx[0],newy[0],ltext,fontdict1,rotation=lrot,va=va,ha=ha)
    plt.text(lx,ly,ltext,fontdict2,rotation=lrot,va=va,ha=ha)

def getProjectedPolygon(polygon,m):
    extlon,extlat = zip(*polygon.exterior.coords[:])
    extx,exty = m(extlon,extlat)
    extpts = list(zip(extx,exty))
    ints = []
    for interior in polygon.interiors:
        try:
            intlon,intlat = zip(*interior.coords[:])
        except:
            x = 1
        intx,inty = m(intlon,intlat)
        ints.append(list(zip(intx,inty)))
    ppolygon = sPolygon(extpts,ints)
    return ppolygon

def getProjectedPolygons(polygon,m):
    polygons = []
    if isinstance(polygon,MultiPolygon):
        for p in polygon:
            ppolygon = getProjectedPolygon(p,m)
            polygons.append(ppolygon)
    else:
        ppolygon = getProjectedPolygon(polygon,m)
        polygons.append(ppolygon)

    return polygons

def getProjectedPatches(polygon,m,edgecolor=WATERCOLOR):
    patches = []
    if isinstance(polygon,MultiPolygon):
        for p in polygon:
            ppolygon = getProjectedPolygon(p,m)
            patch = PolygonPatch(ppolygon,facecolor=WATERCOLOR,edgecolor=edgecolor,
                             zorder=OCEAN_ZORDER,linewidth=1,fill=True,visible=True)
            patches.append(patch)
    else:
        ppolygon = getProjectedPolygon(polygon,m)
        patch = PolygonPatch(ppolygon,facecolor=WATERCOLOR,edgecolor=edgecolor,
                             zorder=OCEAN_ZORDER,linewidth=1,fill=True,visible=True)
        patches.append(patch)

    return patches

class PAGERMap(object):
    def __init__(self,shakegrid,popgrid,cities,layerdict,outfolder):
        """Draw PAGER population/MMI contour map with cities and inset map.

        :param shakegrid:
          ShakeGrid object.
        :param popgrid:
          Grid2D object containing population data.
        :param cities:
          BasemapCities object.
        :param layerdict:
          A dictionary containing file names for:
            - 'coast': Coastline vector data file.
            - 'ocean': Ocean vector data file.
            - 'lake': Ocean vector data file.
            - 'country': Country boundaries vector data file.
            - 'state': State boundaries vector data file.
        :param outfolder:
          Directory where map PNG and PDF files will be written.
        """
        self._shakemap = shakegrid
        self._popgrid = popgrid
        self._cities = cities
        self._layerdict = layerdict
        self._outfolder = outfolder
        self._clipBounds()
        self.fig_width = FIG_WIDTH
        self.fig_height = FIG_HEIGHT
        self.city_cols = CITY_COLS
        self.city_rows = CITY_ROWS
        self.cities_per_grid = CITIES_PER_GRID
        
    def _clipBounds(self):
        #returns a list of GeoJSON-like mapping objects
        xmin,xmax,ymin,ymax = self._shakemap.getBounds()
        bbox = (xmin,ymin,xmax,ymax)
        bboxpoly = sPolygon([(xmin,ymax),(xmax,ymax),(xmax,ymin),(xmin,ymin),(xmin,ymax)])
        self.vectors = {}
        for key,value in self._layerdict.items():
            vshapes = []
            f = fiona.open(value,'r')
            shapes = f.items(bbox=bbox)
            for shapeidx,shape in shapes:
                tshape = sShape(shape['geometry'])
                intshape = tshape.intersection(bboxpoly)
                vshapes.append(intshape)
            f.close()
            self.vectors[key] = vshapes

    def _setMap(self,gd):
        clon = gd.xmin + (gd.xmax-gd.xmin)/2.0
        clat = gd.ymin + (gd.ymax-gd.ymin)/2.0
        f = plt.figure(figsize=(self.fig_width,self.fig_height))
        ax = f.add_axes([0.1,0.1,0.8,0.8])

        m = Basemap(llcrnrlon=gd.xmin,llcrnrlat=gd.ymin,urcrnrlon=gd.xmax,urcrnrlat=gd.ymax,
                    rsphere=(6378137.00,6356752.3142),
                    resolution=BASEMAP_RESOLUTION,projection='merc',
                    lat_0=clat,lon_0=clon,lat_ts=clat,ax=ax,suppress_ticks=True)
        return m

    def _projectGrid(self,data,m,gd):
        #set up meshgrid to project topo and mmi data
        xmin = gd.xmin
        if gd.xmax < gd.xmin:
            xmin -= 360
        lons = np.linspace(xmin, gd.xmax, gd.nx)
        lats = np.linspace(gd.ymax, gd.ymin, gd.ny)  # backwards so it plots right side up
        llons1, llats1 = np.meshgrid(lons, lats)
        pdata = m.transform_scalar(np.flipud(data), lons, lats[::-1], gd.nx, gd.ny, returnxy=False, 
                                   checkbounds=False, order=1, masked=False)
        return pdata

    def _drawBoundaries(self,m):
        allshapes = self.vectors['country'] + self.vectors['state']
        for shape in allshapes:
            #shape is a geojson-like mapping thing
            blon,blat = zip(*shape.coords[:])
            bx,by = m(blon,blat)
            m.plot(bx,by,'k',zorder=BORDER_ZORDER)

    def _drawLakes(self,m,gd):
        lakes = self.vectors['lake']
        for lake in lakes:
            ppatches = getProjectedPatches(lake,m,edgecolor='k')
            for ppatch in ppatches:
                m.ax.add_patch(ppatch)

    def _drawOceans(self,m,gd):
        ocean = self.vectors['ocean'][0] #this is one shapely polygon
        ppatches = getProjectedPatches(ocean,m)
        for ppatch in ppatches:
            m.ax.add_patch(ppatch)

    def _drawCoastlines(self,m,gd):
        coasts = self.vectors['coast']
        for coast in coasts: #these are polygons?
            clon,clat = zip(*coast.exterior.coords[:])
            cx,cy = m(clon,clat)
            m.plot(cx,cy,'k',zorder=BORDER_ZORDER)

    def _drawGraticules(self,m,gd):
        par = np.arange(np.ceil(gd.ymin),np.floor(gd.ymax)+1,1.0)
        mer = np.arange(np.ceil(gd.xmin),np.floor(gd.xmax)+1,1.0)

        xmap_range = m.xmax-m.xmin
        ymap_range = m.ymax-m.ymin
        xoff = -0.09*(xmap_range)
        yoff = -0.04*(ymap_range)
        
        merdict = m.drawmeridians(mer,labels=[0,0,0,1],fontsize=10,xoffset=xoff,yoffset=yoff,
                                  linewidth=0.5,color='gray',zorder=GRATICULE_ZORDER)
        pardict = m.drawparallels(par,labels=[1,0,0,0],fontsize=10,xoffset=xoff,yoffset=yoff,
                                  linewidth=0.5,color='gray',zorder=GRATICULE_ZORDER)

        #loop over meridian and parallel dicts, change/increase font, draw ticks
        xticks = []
        for merkey,mervalue in merdict.items():
            merline,merlablist = mervalue
            merlabel = merlablist[0]
            merlabel.set_family('sans-serif')
            merlabel.set_fontsize(12.0)
            merlabel.set_zorder(GRATICULE_ZORDER)
            xticks.append(merline[0].get_xdata()[0])

        yticks = []
        for parkey,parvalue in pardict.items():
            parline,parlablist = parvalue
            parlabel = parlablist[0]
            parlabel.set_family('sans-serif')
            parlabel.set_fontsize(12.0)
            parlabel.set_zorder(GRATICULE_ZORDER)
            yticks.append(parline[0].get_ydata()[0])

        #plt.tick_params(axis='both',color='k',direction='in')
        plt.xticks(xticks,())
        plt.yticks(yticks,())
        m.ax.tick_params(direction='in')

    def _render_contour_line(self,m,segline,color,linestyle,linewidth):
        if isinstance(segline,(MultiLineString,GeometryCollection)):
            for segment in segline:
                if isinstance(segment,sPolygon):
                    x,y = zip(*segment.exterior.coords)
                else:
                    x,y = zip(*segment.coords)
                    m.plot(x,y,color=color,linestyle=linestyle,linewidth=linewidth,zorder=CONTOUR_ZORDER)
        else:
            if isinstance(segline,sPolygon):
                x,y = zip(*segline.exterior.coords)
            else:
                x,y = zip(*segline.coords)
                m.plot(x,y,color=color,linestyle=linestyle,linewidth=linewidth,zorder=CONTOUR_ZORDER)
        
    def _drawContours(self,m,shakemap):
        #get the projected ocean polygons
        ocean = self.vectors['ocean'][0] #this is one shapely polygon
        ocean_polygons = getProjectedPolygons(ocean,m)
        
        smdata = shakemap.getLayer('mmi').getData().copy()
        smdata = gaussian_filter(smdata,5.0)
        ny,nx = smdata.shape
        lons,lats = m.makegrid(nx,ny)
        x,y = m(lons,lats)
        clevels = np.arange(1.5,11.5,1.0)

        #set up the colors
        #these are the colors for MMI 1-10
        red = np.array([255, 191, 160, 128, 122, 255, 255, 255, 255, 200])
        green = np.array([255, 204, 230, 255, 255, 255, 200, 145,   0,   0])
        blue = np.array([255, 255, 255, 255, 147,   0,   0,   0,   0,   0])

        #we want the colors for MMI 1.5 - 9.5 as well, 
        #so here's some numpy trickery to get those values, and then shuffle them with original arrays
        redhalf = np.concatenate((np.diff(red)/2 + red[0:-1],[0]))
        bluehalf = np.concatenate((np.diff(blue)/2 + blue[0:-1],[0]))
        greenhalf = np.concatenate((np.diff(green)/2 + green[0:-1],[0]))
        red2 = np.ravel(np.array(list(zip(red,redhalf))))[0:-1]/255.0
        green2 = np.ravel(np.array(list(zip(green,greenhalf))))[0:-1]/255.0
        blue2 = np.ravel(np.array(list(zip(blue,bluehalf))))[0:-1]/255.0

        #there is an undocumented C++? class called Cntr() that we can use to
        #generate the contour lines without drawing them first.
        #we want to do this because PAGER contouring requirements are the following:
        #1) Draw the contour lines at half intervals (1.5,2.5, etc.)
        #2) Any part of a contour line that is over water, draw as a dashed line
        #3) Any part of a contour line that is over land, draw as a solid line
        #So, we need to generate the contour lines, figure out which pieces are over water/land,
        #and render them appropriately
        contourobj = cntr.Cntr(x, y, smdata) #here's the undocumented object
        for i in range(0,len(clevels)):
            clevel = clevels[i]
            color = (red2[i],green2[i],blue2[i])
            #you call the trace() method to generate lists of 2D arrays
            #for the contour level of interest
            contour_segments = contourobj.trace(clevel)
            #the last half of the list of contour segments are not sets of coordinates, 
            #so skip them.  Not sure what they are...
            contour_segments = contour_segments[0:len(contour_segments)//2]
            for segment in contour_segments:
                segline = LineString(segment)
                for opoly in ocean_polygons:
                    oceanline = segline.intersection(opoly)
                    landline = segline.symmetric_difference(opoly)
                    self._render_contour_line(m,oceanline,color,'dashed',1)
                    self._render_contour_line(m,landline,color,'solid',2)
                    
    def drawContourMap(self):
        #set up the basemap
        gd = self._popgrid.getGeoDict()
        m = self._setMap(gd)

        #project population grid
        popdata = self._popgrid.getData().copy()
        ptopo = self._projectGrid(popdata,m,gd)

        #draw the population data
        popcmap = getPopColorMap()
        am = m.imshow(ptopo,cmap=popcmap,interpolation='nearest')
        
        #I think I don't need to project the MMI data...
        #draw country/state boundaries
        self._drawBoundaries(m)

        #draw lakes
        self._drawLakes(m,gd)

        #draw oceans
        self._drawOceans(m,gd)

        #draw coastlines
        self._drawCoastlines(m,gd)

        #draw meridians, parallels, labels, ticks
        self._drawGraticules(m,gd)

        #draw map scale
        scalex = gd.xmin + (gd.xmax-gd.xmin)/5.0
        scaley = gd.ymin + (gd.ymax-gd.ymin)/10.0
        yoff = (0.007*(m.ymax-m.ymin))
        clon = (gd.xmin + gd.xmax)/2.0
        clat = (gd.ymin + gd.ymax)/2.0
        m.drawmapscale(scalex,scaley,clon,clat,length=100,barstyle='fancy',yoffset=yoff,zorder=SCALE_ZORDER)

        #draw epicenter
        hlon = self._shakemap.getEventDict()['lon']
        hlat = self._shakemap.getEventDict()['lat']
        m.plot(hlon,hlat,'k*',latlon=True,fillstyle='none',markersize=22,mew=1.2,zorder=EPICENTER_ZORDER)

        #draw cities
        #reduce the number of cities to those whose labels don't collide
        #set up cities
        self._cities = self._cities.limitByBounds((gd.xmin,gd.xmax,gd.ymin,gd.ymax))
        self._cities = self._cities.limitByGrid(nx=self.city_cols,ny=self.city_rows,
                                                cities_per_grid=self.cities_per_grid)
        self._cities = self._cities.limitByMapCollision(m)
        self._cities.renderToMap(m.ax,zorder=CITIES_ZORDER,shadow=True)

        #draw contours of intensity
        self._drawContours(m,self._shakemap)

        #save to a file
        plt.draw()
        outfile = os.path.join(self._outfolder,'pager_contour.pdf')
        print(outfile)
        plt.savefig(outfile)
        
        

        

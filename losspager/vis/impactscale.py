#!/usr/bin/env python

#stdlib imports
from collections import OrderedDict

#third party imports
import matplotlib

#this allows us to have a non-interactive backend - essential on systems without a display
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle,Ellipse


#local imports
from losspager.utils.exception import PagerException

ASPECT = 63/23 #width of old impact scale/height
WIDTH = 8.0 #desired width in inches of new impact scale (doesn't matter much as it's a vector, and we'll scale
#up or down as necessary

GREEN = '#00B04F'
YELLOW = '#FFFF00'
ORANGE = '#FF9900'
RED = '#FF0000'



def _find_renderer(fig):
    if hasattr(fig.canvas, "get_renderer"):
        #Some backends, such as TkAgg, have the get_renderer method, which 
        #makes this easy.
        renderer = fig.canvas.get_renderer()
    else:
        #Other backends do not have the get_renderer method, so we have a work 
        #around to find the renderer.  Print the figure to a temporary file 
        #object, and then grab the renderer that was used.
        #(I stole this trick from the matplotlib backend_bases.py 
        #print_figure() method.)
        import io
        fig.canvas.print_pdf(io.BytesIO())
        renderer = fig._cachedRenderer
    return(renderer)

def drawImpactScale(ranges,losstype,debug=False):
    """Draw a loss impact scale, showing the probabilities that estimated losses fall into one of many bins.

    :param ranges:
      Ordered Dictionary of probability of losses over ranges : 
           '0-1' (green alert)
           '1-10' (yellow alert)
           '10-100' (yellow alert)
           '100-1000' (orange alert)
           '1000-10000' (red alert)
           '10000-100000' (red alert)
           '100000-10000000' (red alert)
    :param losstype:
      String, one of 'fatality' or 'economic'.
    :returns:
      Matplotlib figure containing plot showing probabilities of loss falling into one of the bins listed above.       
    :raises:
      PagerException if input range OrderedDict list of keys is not complete, or
      if ranges is not an OrderedDict.
    """
    req_keys = ['0-1','1-10','10-100','100-1000','1000-10000','10000-100000','100000-10000000']
    if not isinstance(ranges,OrderedDict):
        raise PagerException('Input ranges must be an OrderedDict instance.')
    for key in req_keys:
        if key not in ranges:
            raise PagerException('Input ranges dictionary must have keys: %s' % str(req_keys))

    height = WIDTH/ASPECT
    f = plt.figure(figsize=(WIDTH,height))
    renderer = _find_renderer(f)
    ax = plt.gca()
    plt.axis([0,1,0,1])
    if not debug:
        plt.axis('off')
    #reserve the left edge of the figure for the "sponge ball" - colored circle indicating most likely alert level.
    starting_left_edge = 11/63
    bottom_edge = 7/23
    bottom_bar_height = 3/23
    bar_width = 7/63
    barcolors = [GREEN,YELLOW,YELLOW,ORANGE,RED,RED,RED]
    ticklabels = [1,10,100,1000,10000,100000]
    wfactor = 0
    ticklens = [0.03,0.09,0.03,0.09,0.03,0.09]

    text_widths = []
    inv = ax.transData.inverted()
    for ticklabel in ticklabels:
        t = plt.text(0.5,0.5,format(ticklabel,",d"))
        dxmin,dymin,dwidth,dheight = t.get_window_extent(renderer=renderer).bounds
        dxmax = dxmin + dwidth
        dymax = dymin + dheight
        dataxmin,dataymin = inv.transform((dxmin,dymin))
        dataxmax,dataymax = inv.transform((dxmax,dymax))
        text_widths.append((format(ticklabel,",d"),dataxmax-dataxmin))
        t.remove()

    #draw the bottom bars indicating where the alert levels are
    for barcolor in barcolors:
        left_edge = starting_left_edge + bar_width*wfactor
        rect = Rectangle((left_edge,bottom_edge),bar_width,bottom_bar_height,fc=barcolor,ec='k')
        ax.add_patch(rect)
        if wfactor < len(barcolors)-1:
            ticklen = ticklens[wfactor]
            ticklabel = text_widths[wfactor][0]
            twidth = text_widths[wfactor][1]
            plt.plot([left_edge+bar_width,left_edge+bar_width],[bottom_edge-ticklen,bottom_edge],'k')
            plt.text(left_edge+(bar_width)-(twidth/2.0),bottom_edge-(ticklen+0.07),ticklabel)
        wfactor += 1

    #now draw the top bars
    bottom_edge_bar_top = 10.5/23
    total_height = (23-10.5)/23
    wfactor = 0
    fdict = {'weight':'normal'}
    imax = np.array(list(ranges.values())).argmax()
    for rkey,pvalue in ranges.items():
        if pvalue < 0.03:
            wfactor += 1
            continue
        barcolor = barcolors[wfactor]
        left_edge = starting_left_edge + bar_width*wfactor
        bar_height = (pvalue * total_height)
        lw = 1
        zorder = 1
        if wfactor == imax:
            lw = 3
            zorder = 100
        rect = Rectangle((left_edge,bottom_edge_bar_top),bar_width,bar_height,fc=barcolor,ec='k',lw=lw)
        rect.set_zorder(zorder)
        ax.add_patch(rect)
        ptext = '%i%%' % np.round(pvalue*100)
        plt.text(left_edge+bar_width/2.7,bottom_edge_bar_top+bar_height+0.02,ptext,fontdict=fdict)
        wfactor += 1

    #now draw the sponge ball on the left
    cx = 0.105
    cy = 0.6
    #because our axes is not equal, assuming a circle will be drawn as a circle doesn't work.
    x0, y0 = ax.transAxes.transform((0, 0)) # lower left in pixels
    x1, y1 = ax.transAxes.transform((1, 1)) # upper right in pixes
    dx = x1 - x0
    dy = y1 - y0
    maxd = max(dx, dy)
    width = .11 * maxd / dx
    height = .11 * maxd / dy
    spongecolor = barcolors[imax]
    spongeball = Ellipse((cx,cy),width,height,fc=spongecolor,ec='k',lw=2)
    ax.add_patch(spongeball)
    font = {'style':'italic'}

    #draw units at bottom
    if losstype == 'fatality':
        plt.text(0.5,0.07,'Fatalities',fontdict=font)
    if losstype == 'economic':
        plt.text(0.45,0.07,'USD (Millions)',fontdict=font)

    return f
        
                   

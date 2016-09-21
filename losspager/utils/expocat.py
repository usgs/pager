#!/usr/bin/env python

#stdlib imports
import operator
from datetime import datetime,timedelta
import re
import os.path
from collections import OrderedDict

#third party imports
import pandas as pd
import numpy as np
from impactutils.colors.cpalette import ColorPalette
from openquake.hazardlib.geo.geodetic import geodetic_distance

TIME_WINDOW = 15 #number of seconds to compare one event with another when searching for similar events.
MIN_MMI = 1000

def to_ordered_dict(series):
    keys = series.index
    mydict = OrderedDict()
    for key in keys:
        mydict[key] = series[key]
    return mydict

def _select_by_max_mmi(df,mmi,minimum=1000):
    mmi_indices = {1:'MMI1',2:'MMI2',3:'MMI3',4:'MMI4',5:'MMI5',6:'MMI6',7:'MMI7',8:'MMI8',9:'MMI9+'}
    for idx in np.arange(mmi,10):
        mmicol = mmi_indices[idx]
        anymmi = df[df[mmicol] >= minimum]
        return anymmi
    return None

class ExpoCat(object):
    def __init__(self,dataframe):
        """Create an ExpoCat object from a dataframe input.

        :param dataframe:
          Pandas dataframe containing columns:
            - EventID  14 character event ID based on time: (YYYYMMDDHHMMSS).
            - Time Pandas Timestamp object.
            - Lat  Event latitude.
            - Lon  Event longitude.
            - Depth  Event depth.
            - Magnitude  Event magnitude.
            - CountryCode  Two letter country code in which epicenter is located.
            - ShakingDeaths Number of fatalities due to shaking.
            - TotalDeaths Number of total fatalities.
            - Injured Number of injured.
            - Fire Integer (0 or 1) indicating if any fires occurred as a result of this earthquake.
            - Liquefaction Integer (0 or 1) indicating if any liquefaction occurred as a result of this earthquake.
            - Tsunami Integer (0 or 1) indicating if any tsunamis occurred as a result of this earthquake.
            - Landslide Integer (0 or 1) indicating if any landslides occurred as a result of this earthquake.
            - MMI1 - Number of people exposed to Mercalli intensity 1.
            - MMI2 - Number of people exposed to Mercalli intensity 2.
            - MMI3 - Number of people exposed to Mercalli intensity 3.
            - MMI4 - Number of people exposed to Mercalli intensity 4.
            - MMI5 - Number of people exposed to Mercalli intensity 5.
            - MMI6 - Number of people exposed to Mercalli intensity 6.
            - MMI7 - Number of people exposed to Mercalli intensity 7.
            - MMI8 - Number of people exposed to Mercalli intensity 8.
            - MMI9+ Number of people exposed to Mercalli intensity 9 and above.
            - MaxMMI  Highest intensity level with at least 1000 people exposed.
            - NumMaxMMI Number of people exposed at MaxMMI.
        """
        self._dataframe = dataframe.copy()

    @classmethod
    def fromDefault(cls):
        """Read in data from CSV file included in the distribution of this code.

        :returns:
          ExpoCat object.
        """
        homedir = os.path.dirname(os.path.abspath(__file__)) #where is this module?
        csvfile = os.path.join(homedir,'..','data','expocat.csv')
        return cls.fromCSV(csvfile)
        
    @classmethod
    def fromCSV(cls,csvfile):
        """Read in data from Expocat CSV file.

        :param csvfile:
          CSV file containing columns as described above for constructor, minus the MaxMMI and NumMaxMMI columns.
        :returns:
          ExpoCat object.
        """
        df = pd.read_csv(csvfile,parse_dates=[2],dtype={'EventID':str})
        df = df.drop('Unnamed: 0',1)

        mmicols = ['MMI1','MMI2','MMI3','MMI4','MMI5','MMI6','MMI7','MMI8','MMI9+']
        mmicols.reverse()
        maxmmi = np.zeros(len(df))
        nmaxmmi = np.zeros(len(df))
        for mmicol in mmicols:
            mmival = int(re.search('[0-9]',mmicol).group())
            i_unfilled = maxmmi == 0
            i_meets_min = (df[mmicol] > MIN_MMI).as_matrix()
            intersected = (i_meets_min & i_unfilled)
            maxmmi[intersected] = mmival
            nmaxmmi[intersected] = (df[mmicol].as_matrix())[intersected]
        df['MaxMMI'] = pd.Series(maxmmi)
        df['NumMaxMMI'] = pd.Series(nmaxmmi)
        
        return cls(df)

    def __len__(self):
        """Return the number of rows in this object's dataframe.

        :returns:
          Number of rows in this object's dataframe.
        """
        return len(self._dataframe)

    def __add__(self,other):
        """Add two ExpoCat objects together by concatenating their internal dataframes.

        :param other:
          ExpoCat object.
        :returns:
          An ExpoCat object consisting of events from this ExpoCat object and those from other.
        """
        newdf = pd.concat([self._dataframe,other._dataframe]).drop_duplicates()
        return ExpoCat(newdf)
    
    def getDataFrame(self):
        """Return a copy of the dataframe contained in this ExpoCat object.

        :returns:
          A copy of the dataframe contained in this ExpoCat object.
        """
        return self._dataframe.copy()

    def selectByTime(self,mintime,maxtime):
        """Select down the events in the ExpoCat by restricting to events between two input times.

        :param mintime:
          Pandas Timestamp object OR Python datetime object.
        :param maxtime:
          Pandas Timestamp object OR Python datetime object.
        :returns:
          Reduced ExpoCat set of events to those inside the input time bounds.
        """
        if mintime >= maxtime:
            raise PagerException('Input mintime must be less than maxtime.')
        
        newdf = self._dataframe[(self._dataframe['Time'] > mintime) & (self._dataframe['Time'] <= maxtime)]
        return ExpoCat(newdf)

    def selectByMagnitude(self,minmag,maxmag=None):
        """Select down the events in the ExpoCat by restricting to events between two input magnitudes.

        :param minmag:
          Float earthquake minimum magnitude.
        :param maxmag:
          Float earthquake maximum magnitude.
        :returns:
          Reduced ExpoCat set of events to those inside the input magnitude bounds.
        """
        if maxmag is not None:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag) & (self._dataframe['Magnitude'] <= maxmag)]
        else:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag)]
        return ExpoCat(newdf)

    def selectByBounds(self,xmin,xmax,ymin,ymax):
        """Select down the events in the ExpoCat by restricting to events inside bounding box.

        :param xmin:
          Minimum longitude.
        :param xmax:
          Maximum longitude.
        :param ymin:
          Minimum latitude.
        :param ymax:
          Maximum latitude.
        :returns:
          Reduced ExpoCat set of events to those inside bounding box.
        """
        idx1 = (self._dataframe['Lat'] > ymin)
        idx2 = (self._dataframe['Lat'] <= ymax)
        idx3 = (self._dataframe['Lon'] > xmin)
        idx4 = (self._dataframe['Lon'] <= xmax)
        newdf = self._dataframe[idx1 & idx2 & idx3 & idx4]
        return ExpoCat(newdf)

    def selectByShakingDeaths(self,mindeaths):
        """Select down the events in the ExpoCat by restricting to events with shaking deaths greater than input.

        :param mindeaths:
          Minimum shaking fatality threshold.
        :returns:
          Reduced ExpoCat set of events to those with shaking fatalities greater than mindeaths.
        """
        newdf = self._dataframe[self._dataframe['ShakingDeaths'] >= mindeaths]
        return ExpoCat(newdf)

    def selectByRadius(self,clat,clon,radius):
        """Select events by restricting to those within a search radius around a set of coordinates.

        """
        lons = self._dataframe['Lon']
        lats = self._dataframe['Lat']
        distances = geodetic_distance(clon,clat,lons,lats)
        iclose = pd.Series(distances < radius)
        newdf = self._dataframe[iclose]
        d1 = distances[distances < radius]
        newdf = newdf.assign(Distance=d1)
        return ExpoCat(newdf)
        

    def getHistoricalEvents(self,maxmmi,nmmi,clat,clon):
        """Select three earthquakes from internal list that are "representative" and similar to input event.

        First event should be the event "most similar" in exposure, and with the fewest fatalities.
        Second event should also be "similar" in exposure, and with the most fatalities.
        Third event should be the deadliest and/or highest population exposure event.

        :param maxmmi:
          
        :param clat:
          Origin latitude.
        :param clon:
          Origin latitude.
        :returns:
          List of three dictionaries, containing fields:
            - EventID  14 character event ID based on time: (YYYYMMDDHHMMSS).
            - Time Pandas Timestamp object.
            - Lat  Event latitude.
            - Lon  Event longitude.
            - Depth  Event depth.
            - Magnitude  Event magnitude.
            - CountryCode  Two letter country code in which epicenter is located.
            - ShakingDeaths Number of fatalities due to shaking.
            - TotalDeaths Number of total fatalities.
            - Injured Number of injured.
            - Fire Integer (0 or 1) indicating if any fires occurred as a result of this earthquake.
            - Liquefaction Integer (0 or 1) indicating if any liquefaction occurred as a result of this earthquake.
            - Tsunami Integer (0 or 1) indicating if any tsunamis occurred as a result of this earthquake.
            - Landslide Integer (0 or 1) indicating if any landslides occurred as a result of this earthquake.
            - MMI1 - Number of people exposed to Mercalli intensity 1.
            - MMI2 - Number of people exposed to Mercalli intensity 2.
            - MMI3 - Number of people exposed to Mercalli intensity 3.
            - MMI4 - Number of people exposed to Mercalli intensity 4.
            - MMI5 - Number of people exposed to Mercalli intensity 5.
            - MMI6 - Number of people exposed to Mercalli intensity 6.
            - MMI7 - Number of people exposed to Mercalli intensity 7.
            - MMI8 - Number of people exposed to Mercalli intensity 8.
            - MMI9+ Number of people exposed to Mercalli intensity 9 and above.
            - MaxMMI  Highest intensity level with at least 1000 people exposed.
            - NumMaxMMI Number of people exposed at MaxMMI.
            - Distance Distance of this event from input event, in km.
            - Color The hex color that should be used for row color in historical events table.
        """
        #get the worst event first
        newdf = self._dataframe.sort_values(['ShakingDeaths','MaxMMI','NumMaxMMI'],ascending=False)
        worst = newdf.iloc[0]
        newdf = newdf.drop(newdf.index[[0]]) #get rid of that first row, so we don't re-include the same event
        
        #get the similar but less bad event
        less_bad,newdf = self.getSimilarEvent(newdf,maxmmi,go_down=True)

        #get the similar but worse event
        more_bad,newdf = self.getSimilarEvent(newdf,maxmmi,go_down=False)

        events = []
        colormap = ColorPalette.fromPreset('mmi')
        if less_bad is not None:
            lessdict = to_ordered_dict(less_bad)
            rgbval = colormap.getDataColor(lessdict['MaxMMI'])
            rgb255 = tuple([int(c*255) for c in rgbval])[0:3]
            lessdict['Color'] = '#%02x%02x%02x' % rgb255
            events.append(lessdict)

        if more_bad is not None:
            moredict = to_ordered_dict(more_bad)
            rgbval = colormap.getDataColor(moredict['MaxMMI'])
            rgb255 = tuple([int(c*255) for c in rgbval])[0:3]
            moredict['Color'] = '#%02x%02x%02x' % rgb255
            events.append(moredict)

            
        worstdict = to_ordered_dict(worst)
        rgbval = colormap.getDataColor(worstdict['MaxMMI'])
        rgb255 = tuple([int(c*255) for c in rgbval])[0:3]
        worstdict['Color'] = '#%02x%02x%02x' % rgb255
        events.append(worstdict)

        return events

    def getSimilarEvent(self,df,maxmmi,go_down=True):
        #get all of the events with the same maxmmi as input
        newdf = df[df.MaxMMI == maxmmi]

        #if we're searching for the most similar but less bad event, go_down is True
        newmaxmmi = maxmmi
        if go_down:
            incop = operator.sub
            mmi1 = 1
            mmi2 = 9
            ascending = True
            compop = operator.gt
            decop = operator.add
        else:
            incop = operator.sub
            mmi1 = 9
            mmi2 = 1
            ascending = False
            compop = operator.gt
            decop = operator.add
        while not len(newdf) and compop(newmaxmmi,mmi1):
            newmaxmmi = incop(newmaxmmi,1)
            newdf = df[df.MaxMMI == newmaxmmi]

        if not len(newdf):
            newdf = df[df.MaxMMI == maxmmi]
        newmaxmmi = maxmmi
        while not len(newdf) and compop(newmaxmmi,mmi2):
            newmaxmmi = decop(newmaxmmi,1)
            newdf = df[df.MaxMMI == newmaxmmi]
        if not len(newdf):
            return None
        newdf = newdf.sort_values(['ShakingDeaths','MaxMMI','NumMaxMMI'],ascending=ascending)
        similar = newdf.iloc[0]
        newdf = df.drop(similar.name)
        return (similar,newdf)
        
        


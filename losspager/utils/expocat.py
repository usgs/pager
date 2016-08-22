#!/usr/bin/env python

#stdlib imports
import operator
from datetime import datetime,timedelta

#third party imports
import pandas as pd
import numpy as np

TIME_WINDOW = 15 #number of seconds to compare one event with another when searching for similar events.

def _select_by_max_mmi(df,mmi,minimum=1000):
    mmi_indices = {1:'MMI1',2:'MMI2',3:'MMI3',4:'MMI4',5:'MMI5',6:'MMI6',7:'MMI7',8:'MMI8',9:'MMI9+'}
    for idx in np.arange(mmi,10):
        mmicol = mmi_indices[idx]
        anymmi = df[df[mmicol] >= minimum]
        return anymmi
    return None

class ExpoCat(object):
    def __init__(self,dataframe):
        self._dataframe = dataframe.copy()

    @classmethod
    def loadFromCSV(cls,csvfile):
        df = pd.read_csv(csvfile,parse_dates=[2])
        df = df.rename(columns={'Unnamed: 0':'Index'})
        maxmmi = np.zeros(len(df))
        #df['MaxMMI'] = np.zeros(len(df))
        for idx,row in df.iterrows():
            exparray = np.array([row['MMI1'],row['MMI2'],row['MMI3'],row['MMI4'],
                                 row['MMI5'],row['MMI6'],row['MMI7'],row['MMI8'],row['MMI9+']])

            gt0 = (exparray > 0).nonzero()[0]
            if len(gt0):
                imax = gt0.max()
            else:
                imax = -1
            maxmmi[idx] = imax+1
        df['MaxMMI'] = maxmmi
        return cls(df)

    def __len__(self):
        return len(self._dataframe)

    def __add__(self,other):
        newdf = pd.concat([self._dataframe,other._dataframe]).drop_duplicates()
        return ExpoCat(newdf)
    
    def getDataFrame(self):
        return self._dataframe.copy()

    def selectByTime(self,mintime,maxtime):
        newdf = self._dataframe[(self._dataframe['Time'] > mintime) & (self._dataframe['Time'] <= maxtime)]
        return ExpoCat(newdf)

    def selectByMagnitude(self,minmag,maxmag=None):
        if maxmag is not None:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag) & (self._dataframe['Magnitude'] <= maxmag)]
        else:
            newdf = self._dataframe[(self._dataframe['Magnitude'] > minmag)]
        return ExpoCat(newdf)

    def selectByBounds(self,xmin,xmax,ymin,ymax):
        idx1 = (self._dataframe['Lat'] > ymin)
        idx2 = (self._dataframe['Lat'] <= ymax)
        idx3 = (self._dataframe['Lon'] > xmin)
        idx4 = (self._dataframe['Lon'] <= xmax)
        newdf = self._dataframe[idx1 & idx2 & idx3 & idx4]
        return ExpoCat(newdf)

    def selectByShakingDeaths(self,mindeaths):
        newdf = self._dataframe[self._dataframe['ShakingDeaths'] >= mindeaths]
        return ExpoCat(newdf)

    def selectMostFatal(self):
        dmax = self._dataframe['ShakingDeaths'].max()
        newdf = self._dataframe[self._dataframe['ShakingDeaths'] == dmax]
        return ExpoCat(newdf)

    def selectByMaxMMI(self,mmi,minimum=1000):
        #find all events that have at least minimum population exposed at input MMI or higher
        anymmi = _select_by_max_mmi(self._dataframe,mmi,minimum=minimum)
        if anymmi is not None:
            return ExpoCat(anymmi)
        return None
            
    
    def selectSimilarByExposure(self,maxmmi,nmmi,deaths,search='high',time=None,avoid_ids=[]):
        """Select an earthquake from internal list that is more/less fatal than input and similar in exposure.
        
        :param maxmmi:
          Maximum mmi level (1-10) with at least 1000 people exposed.
        :param nmmi:
          Number of people exposed to maxmmi.
        :param deaths:
          Number of fatalities for input event.
        :param search:
          One of 'high' or 'low'.  
            * If 'high', search for *more* fatal events than this one with a similar
            exposure at maxmmi.  If there are no similar events found at that MMI, search first in 
            successively lower MMI values for similar exposure values (down to MMI 2), then successively higher
            MMI values (up to 10) for similar exposure.

            * If 'low', search for *less* fatal events than this one with a similar
            exposure at maxmmi.  If there are no similar events found at that MMI, search first in 
            successively higher MMI values for similar exposure values (up to MMI 10), then successively lower
            MMI values (down to MMI 2) for similar exposure.

            If no similar earthquakes are found, return None.
        :param time:
          Event datetime - if the user is concerned, this is used to make sure that the returned event is not
          the same as the input event.  Should only be required for generating results from catalog events.
        :param avoid_ids:
          Sequence of EventID values to use to remove undesired rows from consideration 
          (presumably these represent rows that have already been selected for other criteria.)
        """
        #ok, so this is a little tricky, but it saves me from having to write two nearly identical
        #functions.
        #INC_OP1 is the increment operator for the first while loop (up or down in MMI)
        #INC_OP2 is the increment operator for the second while loop (up or down in MMI)
        #INC_COMP1 is the comparison operator for the first while loop (up or down in MMI)
        #INC_COMP2 is the comparison operator for the second while loop (up or down in MMI)
        #DEATH_COMP is the comparison operator for deaths
        #COMP1 is the upper or lower MMI bound we check against in the first while loop
        #COMP2 is the upper or lower MMI bound we check against in the first while loop
        if search == 'low':
            INC_OP1 = operator.sub
            INC_OP2 = operator.add
            INC_COMP1 = operator.gt
            INC_COMP2 = operator.lt
            DEATH_COMP = operator.gt
            MMI_COMP1 = operator.ge
            COMP1 = 1
            COMP2 = 11
        else:
            INC_OP1 = operator.add
            INC_OP2 = operator.sub
            INC_COMP1 = operator.lt
            INC_COMP2 = operator.gt
            DEATH_COMP = operator.le
            MMI_COMP2 = operator.le
            COMP1 = 10
            COMP2 = 1

        mmi_indices = {1:'MMI1',2:'MMI2',3:'MMI3',4:'MMI4',5:'MMI5',6:'MMI6',7:'MMI7',8:'MMI8',9:'MMI9+'}
        #maxmmi is MMI1, 2, 3, etc.
        #nmmi is the number of people at maxmmi
        if time is not None:
            #select out everything BUT the input event (or events really close to it)
            treduce1 = self.selectByTime(datetime(1900,1,1,0,0,0),time-timedelta(seconds=TIME_WINDOW))
            treduce2 = self.selectByTime(time+timedelta(seconds=TIME_WINDOW),datetime.utcnow())
            reduced1 = (treduce1+treduce2).getDataFrame()
        else:
            reduced1 = self._dataframe 

        if len(avoid_ids):
            for eid in avoid_ids:
                reduced1 = reduced1[reduced1['EventID'] != eid]

        #select any events lt or gt the number of deaths we have
        hasdeaths = reduced1[(DEATH_COMP(reduced1['ShakingDeaths'],deaths))]
        newmmi = maxmmi
        #iterate over MMI (up or down, depending on search mode) looking for events with similar MMI
        while INC_COMP1(newmmi,COMP1):
            hasmmi = reduced1[(reduced1['MaxMMI'] == newmmi)]
            reduced2 = (ExpoCat(hasdeaths) + ExpoCat(hasmmi)).getDataFrame()
            if len(reduced2):
                #find the event with the most similar exposure at maxmmi
                mmi_idx = mmi_indices[newmmi]
                similar_exp = _select_by_max_mmi(reduced2,newmmi)
                if len(similar_exp):
                    #find the event with the most similar exposure at this MMI
                    immi = np.abs(similar_exp[mmi_idx].as_matrix()-nmmi).argmin()
                    similar = similar_exp.iloc[immi]
                    return similar
            newmmi = INC_OP1(newmmi,1)

        newmmi = maxmmi
        while INC_COMP2(newmmi,COMP2):
            hasmmi = reduced1[(reduced1['MaxMMI'] == newmmi)]
            reduced2 = (ExpoCat(hasdeaths) + ExpoCat(hasmmi)).getDataFrame()
            if len(reduced2):
                #find the event with the most similar exposure at maxmmi
                mmi_idx = mmi_indices[newmmi]
                similar_exp = _select_by_max_mmi(reduced2,newmmi)
                if len(similar_exp):
                    #find the event with the most similar exposure at this MMI
                    immi = np.abs(similar_exp[mmi_idx].as_matrix()-nmmi).argmin()
                    similar = similar_exp.iloc[immi]
                    return similar
            newmmi = INC_OP2(newmmi,1)

        return None

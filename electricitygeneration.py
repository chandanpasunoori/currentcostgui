# -*- coding: utf-8 -*-

#
# CurrentCost GUI
#
#    Copyright (C) 2008  Dale Lane
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  The author of this code can be contacted at Dale.Lane@gmail.com
#    Any contact about this application is warmly welcomed.
#

import numpy as np
import time
from threading import Thread, Lock, Condition


from gridsourcedata     import ElectricityGenerationDataSource
from tracer             import CurrentCostTracer

# this class provides logging and diagnostics
trc = CurrentCostTracer()


#
# Displays a graph showing live CurrentCost data divided by the way the 
#   electricity was generated. 
#
#  Dale Lane (http://dalelane.co.uk/blog)
#
class CurrentCostElectricityGeneration():

    livegraph = None

    energyMix = { 'CCGT'     : 0.0000000000000000000000000001,
                  'OCGT'     : 0.0000000000000000000000000001,
                  'OIL'      : 0.0000000000000000000000000001,
                  'COAL'     : 0.0000000000000000000000000001,
                  'NUCLEAR'  : 0.0000000000000000000000000001,
                  'WIND'     : 0.0000000000000000000000000001,
                  'PS'       : 0.0000000000000000000000000001,
                  'NPSHYD'   : 0.0000000000000000000000000001,
                  'OTHER'    : 0.0000000000000000000000000001,
                  'INTFR'    : 0.0000000000000000000000000001,
                  'INTIRL'   : 0.0000000000000000000000000001,
                  'UNKNOWN'  : 100 }

    emxClient = None

    def startBackgroundThread(self):
        if self.emxClient != None:
            self.stopBackgroundThread()
        self.emxClient = GridGenerationUpdateThread(self)
        self.emxClient.start()

    def stopBackgroundThread(self):
        global trc
        if self.emxClient != None:
            self.emxClient.stopUpdates()
            self.energyMix = { 'CCGT'     : 0.0000000000000000000000000001,
                               'OCGT'     : 0.0000000000000000000000000001,
                               'OIL'      : 0.0000000000000000000000000001,
                               'COAL'     : 0.0000000000000000000000000001,
                               'NUCLEAR'  : 0.0000000000000000000000000001,
                               'WIND'     : 0.0000000000000000000000000001,
                               'PS'       : 0.0000000000000000000000000001,
                               'NPSHYD'   : 0.0000000000000000000000000001,
                               'OTHER'    : 0.0000000000000000000000000001,
                               'INTFR'    : 0.0000000000000000000000000001,
                               'INTIRL'   : 0.0000000000000000000000000001,
                               'UNKNOWN'  : 100 }



    def initialiseGraph(self, dates, data, targetPage, formatter):
        global trc
        trc.FunctionEntry("electricitygeneration :: initialiseGraph")

        trc.Trace("energy mix ratios : " + str(self.energyMix))

        # prepare graph for drawing
        self.livegraph = targetPage
        self.livegraph.set_ylabel('kW')
        self.livegraph.grid(True)
        self.livegraph.set_title('Where did your electricity come from?')
        self.livegraph.set_autoscale_on = False
        colormap = [ '#0000FF', '#00FF00', '#FF0000', '#00FFFF', '#2277AA', '#9911BB', '#FFFF00', '#FF00FF', '#550011', '#110066', '#CCCCCC', '#F0F0F0' ]
        self.stacked_graph(dates, data, colormap)
        for label in self.livegraph.get_xticklabels():
            label.set_rotation(90)
        self.livegraph.xaxis.set_major_formatter(formatter)
        self.livegraph.xaxis.set_minor_formatter(formatter)
        self.livegraph.legend(loc='upper left', fancybox=True, shadow=True, ncol=2)
        trc.FunctionExit("electricitygeneration :: initialiseGraph")
    

    def splitBySource(self, reading):        
        split = { 'CCGT'     : (self.energyMix['CCGT'] / 100) * reading, 
                  'OCGT'     : (self.energyMix['OCGT'] / 100) * reading, 
                  'OIL'      : (self.energyMix['OIL'] / 100) * reading, 
                  'COAL'     : (self.energyMix['COAL'] / 100) * reading, 
                  'NUCLEAR'  : (self.energyMix['NUCLEAR'] / 100) * reading, 
                  'WIND'     : (self.energyMix['WIND'] / 100) * reading, 
                  'PS'       : (self.energyMix['PS'] / 100) * reading, 
                  'NPSHYD'   : (self.energyMix['NPSHYD'] / 100) * reading, 
                  'OTHER'    : (self.energyMix['OTHER'] / 100) * reading, 
                  'INTFR'    : (self.energyMix['INTFR'] / 100) * reading, 
                  'INTIRL'   : (self.energyMix['INTIRL'] / 100) * reading, 
                  'UNKNOWN'  : (self.energyMix['UNKNOWN'] / 100) * reading }
        return split


    def stacked_graph(self, timeset, graphdata, colormap):
        global trc
        trc.FunctionEntry("stacked_graph")

        CCGT = []
        OCGT = []
        OIL  = []
        COAL = []
        NUCLEAR = [] 
        WIND = []
        PS = [] 
        NPSHYD = [] 
        OTHER = [] 
        INTFR = [] 
        INTIRL = []
        UNKNOWN = []

        for ccread in graphdata:
            CCGT.append(ccread['CCGT'])
            OCGT.append(ccread['OCGT'])
            OIL.append(ccread['OIL'])
            COAL.append(ccread['COAL'])
            NUCLEAR.append(ccread['NUCLEAR'])
            WIND.append(ccread['WIND'])
            PS.append(ccread['PS'])
            NPSHYD.append(ccread['NPSHYD']) 
            OTHER.append(ccread['OTHER']) 
            INTFR.append(ccread['INTFR']) 
            INTIRL.append(ccread['INTIRL'])
            UNKNOWN.append(ccread['UNKNOWN'])
        
        streams = np.asarray([ CCGT,   OCGT,   OIL,   COAL,   NUCLEAR,   WIND,   PS,   NPSHYD,   OTHER,   INTFR,   INTIRL,   UNKNOWN ])
        labels  =            [ "CCGT", "OCGT", "OIL", "COAL", "NUCLEAR", "WIND", "PS", "NPSHYD", "OTHER", "INTFR", "INTIRL", "UNKNOWN" ]

        numentries = len(timeset)
        for i in range(numentries - 1, -1, -1):
            timeset.append(timeset[i])

        zeroline         = np.zeros(numentries)
        firststream      = streams[0]
        secondstream     = -streams[1]
        remainingstreams = streams[2:]

        lowerbounds = np.vstack( (zeroline, firststream)  )
        nextbounds  = np.vstack( (secondstream, zeroline) )

        stream_bounds = [ lowerbounds, nextbounds ]

        side = -1
        for stream in remainingstreams:
            side *= -1
            if side == 1:
                prevstream = stream_bounds[-2][1]
                nextstream = prevstream + stream
                nextbounds = np.vstack( (prevstream, nextstream) )
            else:
                prevstream = stream_bounds[-2][0]
                nextstream = prevstream - stream
                nextbounds = np.vstack( (nextstream, prevstream) )
            stream_bounds.append(nextbounds)

        stream_bounds = np.array(stream_bounds)
        baseline      = np.min(stream_bounds[:,0,:], axis=0)

        for i in range(len(stream_bounds)):
            bound = stream_bounds[i]
            xvalues = timeset
            yvalues = np.hstack(( bound[0] - baseline, (bound[1] - baseline)[::-1] ))
            self.livegraph.fill(xvalues, yvalues, 
                                label     = labels[i],
                                facecolor = colormap[i], 
                                edgecolor = 'black',
                                linewidth = 0.1)

        trc.FunctionExit("stacked_graph")



# a background thread
class GridGenerationUpdateThread(Thread):
    disconnect = False
    elecgen    = None
    sleeper    = None
    def __init__(self, parent):
        Thread.__init__(self)
        self.disconnect = False
        self.elecgen = parent
        self.ngdata  = ElectricityGenerationDataSource()
        self.sleeper = Condition()
    def stopUpdates(self):
        self.disconnect = True
        self.sleeper.acquire()
        self.sleeper.notify()
        self.sleeper.release()
    def run(self):
        while self.disconnect == False:
            emxml = self.ngdata.DownloadRealtimeXML()
            try: 
                self.elecgen.energyMix = self.ngdata.ParseRealtimeXML(emxml)
            except Exception, exc:
                trc.Error("failed to parse realtime xml")
                trc.Error(str(emxml))
                trc.Error(repr(exc))
                trc.Error(repr(exc.message))
            # go to sleep for a while - the realtime data doesn't update very
            #  often, so no need to download it constantly!
            self.sleeper.acquire()
            self.sleeper.wait(180)
            self.sleeper.release()

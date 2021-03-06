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
import wx
import csv
import datetime
import time
import pytz

from matplotlib.dates import DayLocator, HourLocator, MinuteLocator, DateFormatter, num2date
from matplotlib.ticker import FuncFormatter, ScalarFormatter
from matplotlib.widgets import SpanSelector
from threading import Thread, Lock

from currentcostcomlive    import CurrentCostSerialLiveConnection
from nationalgriddata      import NationalGridDataSource
from electricitygeneration import CurrentCostElectricityGeneration
from tracer                import CurrentCostTracer


# this class provides logging and diagnostics
trc = CurrentCostTracer()


#ZERO = datetime.timedelta(0)
#HOUR = datetime.timedelta(hours=1)##

#class UTC(datetime.tzinfo):
#    def utcoffset(self, dt):
#        return ZERO
#    def tzname(self, dt):
#        return "UTC"
#    def dst(self, dt):
#        return ZERO#

#utc = UTC()

#
# Displays a graph showing live CurrentCost data. 
#
#  Dale Lane (http://dalelane.co.uk/blog)
#
class CurrentCostLiveData():
    #
    # where are we getting live data from?
    CONNECTION_NONE   = 0
    CONNECTION_MQTT   = 1
    CONNECTION_SERIAL = 2

    connectionType = CONNECTION_NONE
    closing = False

    #
    # which other live feeds should be shown?
    showNationalGridDemand = False
    showNationalGridFrequency = False

    # graphs where the live data is shown
    livegraph = None
    livegraphNGDemand    = None
    livegraphNGFrequency = None

    #
    # handle to the GUI where the graph is shown
    guicallback = None

    #
    # live data store - dates and the readings
    #  assuming equivalent indices - e.g. the third date goes with
    #       the third reading
    ccdates = []
    ccreadings = []
    ccsplitreadings = []

    #
    # National Grid data store - dates and the readings
    #  assuming equivalent indices - e.g. the third date goes with
    #       the third reading
    ngdatadates = []
    ngdemandreadings = []
    ngfreqreadings = []
    ngfreqzeroline = []

    # 
    # likely limits for National Grid frequency data
    # 
    # taken from http://www.nationalgrid.com/uk/Electricity/Data/Realtime/
    #
    NGFREQ_MIN  = 49.8
    NGFREQ_ZERO = 50.00
    NGFREQ_MAX  = 50.2

    # background threads actually getting the live data
    mqttClient = None
    comClient  = None
    ngdClient  = None

    genClient  = CurrentCostElectricityGeneration()

    # when did we start tracking live data?
    starttime = None

    # how should we display labels on the axes?
    stddatefmtter = DateFormatter('%H:%M.%S')
    freqfmtter    = None

    # there can be two threads updating the graph. to avoid them both doing it 
    #  at once, we need a thread lock
    lock = Lock()

    # if a modal dialog is open we should stop redrawing graphs
    dlgOpen = False

    # handle to db used to persist data
    appDatabase = None

    def ExportLiveData(self, filepath):
        f = open(filepath, 'wt')
        fieldnames = ('Time', 'kWH')
        writer = csv.DictWriter(f, fieldnames=fieldnames, dialect='excel')
        headers = {}
        for n in fieldnames:
            headers[n] = n
        writer.writerow(headers)

        for i in range(0, len(self.ccdates) - 1):
            writer.writerow( { 'Time': self.ccdates[i],
                               'kWH' : self.ccreadings[i] } )

        f.close()        


    #
    # redraw all active graphs
    # 
    def redrawGraph(self):
        global trc
        trc.FunctionEntry("currentcostlivedata :: redrawGraph")

        if self.dlgOpen:
            trc.Trace("dialog is open")
            trc.FunctionExit("currentcostlivedata :: redrawGraph")
            return

        trc.Trace(str(len(self.ccdates)) + " dates and " + 
                  str(len(self.ccreadings)) + " data points")

        trc.Trace("aquiring lock")
        self.lock.acquire()

        #
        # Step 1:
        #   update the graph plots
        # 
        if len(self.ccdates) > 0:
            try:
                trc.Trace("plotting live data")
                self.livegraph.plot_date(self.ccdates, 
                                         self.ccreadings,
                                         'r-')
            except Exception, e:
                trc.Trace("failed to plot data on live graph")
                trc.Trace(str(e))
                trc.Trace(str(e.message))
                if self.closing == False:
                    trc.Error('Failed to plot data on livegraph')
                    trc.Error(str(e))
                    trc.Error(str(e.message))
                    trc.Error("have " + str(len(self.ccdates)) + " dates and " + 
                              str(len(self.ccreadings)) + " data points")
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False
        else:
            trc.Trace("no dates to plot")

        
        if self.livegraphNGDemand != None and len(self.ngdatadates) > 0:
            try:
                # update the graph
                trc.Trace("plotting National Grid demand data")
                self.livegraphNGDemand.plot_date(self.ngdatadates, 
                                                 self.ngdemandreadings,
                                                 'b-')
            except Exception, e:
                trc.Error('DEBUG: error - failed to plot demand data on national grid graph')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False

        if self.livegraphNGFrequency != None and len(self.ngdatadates) > 0:
            try:
                # update the graph
                trc.Trace("plotting National Grid frequency data")
                self.livegraphNGFrequency.plot_date(self.ngdatadates, 
                                                    self.ngfreqreadings,
                                                    'b-')

                # add a 'zero' (e.g. 50Hz) line to the graph
                # I tried to do this using axhline but it threw some weird 
                #  ordinal must be >= 1 errors when I tried doing any additional
                #  plots. This is a fairly hacky workaround
                trc.Trace("plotting zero line")
                self.livegraphNGFrequency.plot_date(self.ngdatadates, 
                                                    self.ngfreqzeroline,
                                                    'g-')
            except Exception, e:
                trc.Error('DEBUG: error - failed to plot frequency data on national grid graph')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False

        #
        # Step 2: 
        #   disable auto-scaling
        #    there is a bug when use twinx to plot data series for multiple y
        #    axes on a single graph. the scaling sometimes gets out of sync, so
        #    you get two x-axes overlaid on each other, with slightly different
        #    zoom factors
        # 
        #    so we scale all x-axes manually
        # 
        trc.Trace("disabling auto-scaling")
        if len(self.ccdates) > 0:
            self.livegraph.set_autoscale_on = False
        if self.livegraphNGDemand != None:
            self.livegraphNGDemand.set_autoscale_on = False            
        if self.livegraphNGFrequency != None:
            self.livegraphNGFrequency.set_autoscale_on = False
        
        #
        # Step 3:
        #   rotate labels on x-axis
        #    makes the timestamps fit better when rendered vertically
        # 
        try:
            trc.Trace("rotating labels on x-axis")
            for label in self.livegraph.get_xticklabels():
                label.set_rotation(90)
        except Exception, e:
            trc.Error('DEBUG: error - failed to rotate axis labels on live graph')
            trc.Error(str(e))
            trc.Error(str(e.message))
            trc.Trace("releasing lock")
            self.lock.release()
            trc.FunctionExit("currentcostlivedata :: redrawGraph")
            return False
        if self.livegraphNGDemand != None:
            try:
                trc.Trace("rotating labels on x-axis for National Grid demand data")
                for label in self.livegraphNGDemand.get_xticklabels():
                    label.set_rotation(90)
            except Exception, e:
                trc.Error('DEBUG: error - failed to rotate axis labels on NG demand graph')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False
        if self.livegraphNGFrequency != None:
            try:
                trc.Trace("rotating labels on x-axis for National Grid frequency data")
                for label in self.livegraphNGFrequency.get_xticklabels():
                    label.set_rotation(90)
            except Exception, e:
                trc.Error('DEBUG: error - failed to rotate axis labels on NG frequency graph')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False
        
        #
        # Step 4:
        #   manually zoom all graphs to same scale - keeping x-axes in sync
        # 
        trc.Trace("setting xmin/xmax")
        endtime = datetime.datetime.now(pytz.utc)
        self.livegraph.set_xlim(xmin=self.starttime, xmax=endtime)
        if self.livegraphNGDemand != None:
            self.livegraphNGDemand.set_xlim(xmin=self.starttime, xmax=endtime)
        if self.livegraphNGFrequency != None:
            self.livegraphNGFrequency.set_xlim(xmin=self.starttime, xmax=endtime)
            self.livegraphNGFrequency.set_ylim(ymin=self.NGFREQ_MIN, ymax=self.NGFREQ_MAX)
        
        #
        # Step 5:
        #   format x-axis labels
        #    don't know how to switch one of these off, so we create multiple
        #    identical axes, and try to ignore the fact that you can see it's
        #    slightly thicker as drawn twice in the same place!
        try:
            # format the dates on the x-axis
            if len(self.ccdates) > 0:
                trc.Trace("formatting x-axis labels")
                self.livegraph.xaxis.set_major_formatter(self.stddatefmtter)
                self.livegraph.xaxis.set_minor_formatter(self.stddatefmtter)
            if self.livegraphNGDemand != None:
                trc.Trace("formatting x-axis labels for National Grid demand")
                self.livegraphNGDemand.xaxis.set_major_formatter(self.stddatefmtter)
                self.livegraphNGDemand.xaxis.set_minor_formatter(self.stddatefmtter)
            if self.livegraphNGFrequency != None:
                trc.Trace("formatting x-axis labels for National Grid frequency")
                self.livegraphNGFrequency.xaxis.set_major_formatter(self.stddatefmtter)
                self.livegraphNGFrequency.xaxis.set_minor_formatter(self.stddatefmtter)
                self.livegraphNGFrequency.yaxis.set_major_formatter(self.freqfmtter)
                for line in self.livegraphNGFrequency.get_yticklines():
                    line.set_markersize(0)
        except Exception, e:
            trc.Error('DEBUG: error - failed to assign xaxis formatters')
            trc.Error(str(e))
            trc.Error(str(e.message))
            trc.Trace("releasing lock")
            self.lock.release()
            trc.FunctionExit("currentcostlivedata :: redrawGraph")
            return False
        
        #
        # Step 6:
        #   final step - redraw all active graphs
        # 
        try:
            trc.Trace("redrawing canvas")
            self.livegraph.figure.canvas.draw()
        except Exception, e:
            trc.Error('DEBUG: error - failed to redraw live canvas')
            trc.Error(str(e))
            trc.Error(str(e.message))
            trc.Trace("releasing lock")
            self.lock.release()
            trc.FunctionExit("currentcostlivedata :: redrawGraph")
            return False
        if self.livegraphNGDemand != None:
            try:
                trc.Trace("redrawing National Grid demand canvas")
                self.livegraphNGDemand.figure.canvas.draw()
            except Exception, e:
                trc.Error('DEBUG: error - failed to redraw NG demand canvas')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False
        if self.livegraphNGFrequency != None:
            try:
                trc.Trace("redrawing National Grid frequency canvas")
                self.livegraphNGFrequency.figure.canvas.draw()
            except Exception, e:
                trc.Error('DEBUG: error - failed to redraw NG frequency canvas')
                trc.Error(str(e))
                trc.Error(str(e.message))
                trc.Trace("releasing lock")
                self.lock.release()
                trc.FunctionExit("currentcostlivedata :: redrawGraph")
                return False
        
        #
        # graph redraw complete
        trc.Trace("releasing lock")
        self.lock.release()
        trc.FunctionExit("currentcostlivedata :: redrawGraph")
        return True


    #
    # called when another CurrentCost reading is available
    # 
    #  the new reading is appended to the set, and the graph is refreshed
    # 
    def updateGraph(self, ccreading):
        global trc
        trc.FunctionEntry("currentcostlivedata :: updateGraph")

        trc.Trace("new data: " + str(ccreading))

        if ccreading > 0:
            # store the new reading
            try:                
                x = datetime.datetime.now(pytz.utc)
                trc.Trace("timestamp : " + repr(x))
                self.ccdates.append(x)
                self.ccreadings.append(ccreading)
                self.ccsplitreadings.append(self.genClient.splitBySource(ccreading))
                trc.Trace("stored reading")
            except Exception, err:
                trc.Error("failed to store live reading")
                trc.Error(str(err))
              
            # redraw the graph with the new reading
            self.redrawGraph()
        else:
            trc.Trace("ignoring zero reading")

        trc.FunctionExit("currentcostlivedata :: updateGraph")

    #
    # prepare the graph used to display live CurrentCost data
    # 
    def prepareCurrentcostDataGraph(self, graphaxes):
        global trc
        trc.FunctionEntry("currentcostlivedata :: prepareCurrentcostDataGraph")
        
        # prepare graph for drawing
        self.livegraph = graphaxes
        self.livegraph.set_ylabel('kW')
        self.livegraph.grid(True)
        self.livegraph.set_autoscale_on = False

        trc.FunctionExit("currentcostlivedata :: prepareCurrentcostDataGraph")

    #
    # called to create a connection to the CurrentCost meter
    # 
    def connect(self, guihandle, connType, ccdb, graphaxes, ipaddr, topic, com):
        global trc
        trc.FunctionEntry("currentcostlivedata :: connect")

        self.appDatabase = ccdb

        # start background thread
        qDlg = wx.MessageDialog(guihandle, 
                                "Would you like to download National Grid generation data? (Requires an Internet connection).\n" +
                                " If 'Yes', this will download data about the source of National Grid electricity while Live data is collected.\n" + 
                                " Click on 'Show live data' -> 'National electricity generation' to display data collected", 
                                "CurrentCost", 
                                style=(wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION))
        dwldResponse = qDlg.ShowModal()
        qDlg.Destroy()

        trc.Trace("user response to National Grid question: " + repr(dwldResponse))

        if dwldResponse == wx.ID_YES:
            trc.Trace("starting background thread for National Grid data")
            self.genClient.startBackgroundThread()

        # store globals
        self.connectionType = connType
        self.livegraph = graphaxes
        self.guicallback = guihandle

        # prepare graph for drawing
        trc.Trace("preparing livegraph cla")
        self.livegraph.cla()
        self.prepareCurrentcostDataGraph(graphaxes)

        if self.starttime == None:
            trc.Trace("no starttime - setting a starttime now")
            self.starttime = datetime.datetime.now(pytz.utc)

        if self.connectionType == self.CONNECTION_MQTT:
            trc.Trace("connection type: MQTT")
            self.ipaddress = ipaddr
            self.topicstring = topic
    
            mqttClientModule = __import__("currentcostmqttlive")
            self.mqttClient = mqttClientModule.CurrentCostMQTTLiveConnection()
    
            backgroundThread = MQTTUpdateThread(self.mqttClient, ipaddr, topic, self)
            backgroundThread.start()
        elif self.connectionType == self.CONNECTION_SERIAL:
            trc.Trace("connection type: serial")
            self.comport = com

            trc.Trace("creating serial connection for live data")
            self.comClient = CurrentCostSerialLiveConnection()

            trc.Trace("creating background thread for CurrentCost data")
            backgroundThread = SerialUpdateThread(self.comClient, com, self)
            backgroundThread.start()
        else:
            trc.Error("unsupported connection type : " + str(self.connectionType))


        trc.Trace("currentcostlivedata :: creating span selector")
        span = SpanSelector(self.livegraph, self.onselect, 'horizontal', useblit=True,
                            rectprops=dict(alpha=0.5, facecolor='red'))

        trc.FunctionExit("currentcostlivedata :: connect")


    # 
    # called to disconnect from the CurrentCost meter
    # 
    #  existing graph should be left untouched
    # 
    def disconnect(self):
        global trc
        trc.FunctionEntry("currentcostlivedata :: disconnect")
        self.closing = True
        
        if self.connectionType == self.CONNECTION_MQTT:
            if self.mqttClient != None:
                self.mqttClient.Disconnect()
        elif self.connectionType == self.CONNECTION_SERIAL:
            if self.comClient != None:
                self.comClient.Disconnect()

        if self.ngdClient != None:
            self.ngdClient.stopUpdates()

        self.genClient.stopBackgroundThread()

        # re-initialise variables
        self.connectionType = self.CONNECTION_NONE
        self.livegraph = None

        trc.FunctionExit("currentcostlivedata :: disconnect")

    #
    # called to return an error to the GUI for displaying to the user
    # 
    #  we disconnect before displaying the error
    # 
    def exitOnError(self, errmsg):
        global trc
        trc.FunctionEntry("currentcostlivedata :: exitOnError")
        self.disconnect()
        if (self.guicallback != None):
            self.guicallback.displayLiveConnectFailure(errmsg)
        trc.Trace("error message : " + str(errmsg))
        trc.FunctionExit("currentcostlivedata :: exitOnError")


    #
    # called when another National Grid data is available
    # 
    #  the new reading is appended to the set, and the graph is refreshed
    # 
    def updateNationalGridGraph(self, ngdemand, ngfrequency):

        # store the new National Grid data readings
        if ngdemand != None and ngfrequency != None:
            self.ngdatadates.append(datetime.datetime.now(pytz.utc))
            self.ngdemandreadings.append(ngdemand)
            self.ngfreqreadings.append(ngfrequency)
            self.ngfreqzeroline.append(self.NGFREQ_ZERO)
    
            # if we are also plotting live CurrentCost readings, we allow the 
            #  CurrentCost update function to redraw the graph (otherwise, 
            #  having two threads redrawing the graph at the same time tends to
            #  screw matplotlib up). 
            # if we are only plotting National Grid data, then we need to redraw
            #  the graph now
            if self.connectionType == self.CONNECTION_NONE:
                self.redrawGraph()



    #
    # start the download and display of national electricity demand
    #  data from the National Grid
    # 
    def startNationalGridDemandData(self, livegraphaxes):
        
        if self.showNationalGridDemand == False:
            # we are not currently showing national demand data, but we 
            #  are about to start
            self.showNationalGridDemand = True

            # if this is a new graph, we need to make a note of the 
            #  far-left x-axis value for zooming purposes
            if self.starttime == None:
                self.starttime = datetime.datetime.now(pytz.utc)

            # store a handle to the parent graph if required (only if we 
            #  are viewing National Grid data without personal CurrentCost data)
            if livegraphaxes != None:
                self.livegraph = livegraphaxes

            # we (currently) cannot show both demand and frequency on the same 
            #  graph. so if there is an existing graph for frequency data, we
            #  need to delete it now
            if self.livegraphNGFrequency != None:
                self.livegraphNGFrequency = None

            # if we are re-starting an existing graph, we don't need to create
            #  the axes to draw on.
            # otherwise, we create them now
            if self.livegraphNGDemand == None:
                self.livegraphNGDemand = self.livegraph.twinx()                
                self.livegraphNGDemand.set_ylabel('UK electricity demand (MW)')

            # create a background thread that will poll the National Grid
            #  website and return national electricity demand values
            if self.ngdClient == None:
                self.ngdClient = NationalGridUpdateThread(self)
                self.ngdClient.start()

    #
    # stop the download and display of national electricity demand
    #  data from the National Grid
    # 
    def stopNationalGridDemandData(self):
        
        if self.showNationalGridDemand == True:
            # we are currently showing national demand data, but we are 
            #   about to stop
            self.showNationalGridDemand = False

            # stop the background thread
            self.ngdClient.stopUpdates()

            # delete the background thread object
            self.ngdClient = None

    #
    # stop the display of national electricity demand
    #  data from the National Grid
    # 
    def pauseNationalGridDemandData(self):
        
        if self.showNationalGridDemand == True:
            # we are currently showing national demand data, but we are 
            #   about to stop
            self.showNationalGridDemand = False


    #
    # start the download and display of national electricity frequency
    #  data from the National Grid
    # 
    def startNationalGridFrequencyData(self, livegraphaxes):

        if self.showNationalGridFrequency == False:
            # we are not currently showing national frequency data, but we 
            #  are about to start
            self.showNationalGridFrequency = True

            # if this is a new graph, we need to make a note of the 
            #  far-left x-axis value for zooming purposes
            if self.starttime == None:
                self.starttime = datetime.datetime.now(pytz.utc)

            # store a handle to the parent graph if required (only if we 
            #  are viewing National Grid data without personal CurrentCost data)
            if livegraphaxes != None:
                self.livegraph = livegraphaxes

            # we (currently) cannot show both demand and frequency on the same 
            #  graph. so if there is an existing graph for demand data, we
            #  need to delete it now
            if self.livegraphNGDemand != None:
                self.livegraphNGDemand = None

            # if we are re-starting an existing graph, we don't need to create
            #  the axes to draw on.
            # otherwise, we create them now
            if self.livegraphNGFrequency == None:
                self.livegraphNGFrequency = self.livegraph.twinx()
                self.livegraphNGFrequency.set_ylabel('UK national electricity supply vs demand')
                self.freqfmtter = FuncFormatter(self.formatFrequencyData)

            # create a background thread that will poll the National Grid
            #  website and return national electricity demand values
            if self.ngdClient == None:
                self.ngdClient = NationalGridUpdateThread(self)
                self.ngdClient.start()

    #
    # stop the download and display of national electricity frequency
    #  data from the National Grid
    # 
    def stopNationalGridFrequencyData(self):

        if self.showNationalGridFrequency == True:
            # we are currently showing national frequency data, but we are 
            #   about to stop
            self.showNationalGridFrequency = False

            # stop the background thread
            self.ngdClient.stopUpdates()

            # delete the background thread object
            self.ngdClient = None

    #
    # stop the display of national electricity frequency data from the 
    #  National Grid
    # 
    def pauseNationalGridFrequencyData(self):

        if self.showNationalGridFrequency == True:
            # we are currently showing national frequency data, but we are 
            #   about to stop
            self.showNationalGridFrequency = False


    #
    # custom axis label formatter - used to transform a frequency Hz value for
    #  the National Grid power supply into it's meaning in terms of national 
    #  electricity supply vs demand.
    # 
    # meaning taken from http://dynamicdemand.co.uk/grid.htm
    # 
    def formatFrequencyData(self, x, pos=None):
        if round(x, 2) == 50.00:
            return 'supply = demand'
        elif round(x, 2) == 49.90:
            return 'supply > demand'
        elif round(x, 2) == 50.10:
            return 'supply < demand'
        else:
            return ''

    def prepareElectricitySourceGraph(self, targetTab):
        global trc
        trc.FunctionEntry("prepareElectricitySourceGraph")
        # TODO - protect against empty data
        self.genClient.initialiseGraph(list(self.ccdates), 
                                       list(self.ccsplitreadings),
                                       targetTab, 
                                       self.stddatefmtter)
        trc.FunctionExit("prepareElectricitySourceGraph")



    #
    # calculate how much electricity was used between the span of the graph
    #  selected by the user
    # 
    # xmin,xmax identify the x values of the range in the graph span
    # 
    def onselect(self, xmin, xmax):
        global trc
        trc.FunctionEntry("currentcostlivedata :: onselect")
        trc.Trace("xmin : " + repr(xmin) + ", xmax : " + repr(xmax))

        datelo = num2date(xmin)
        datehi = num2date(xmax)
        dateloReading = None
        datehiReading = None

        onesecond = 1.0 / 3600.0
        totalUsage = 0.0

        # note: it's safe to assume that self.ccdates is already sorted
        for idx, nextReading in enumerate(self.ccdates):
            if nextReading < datelo:
                dateloReading = idx
                delta = self.ccdates[idx + 1] - self.ccdates[idx]
                trc.Trace("A : " + repr(self.ccreadings[idx]) + " for " + repr(delta.seconds) + " seconds")
                timeInHours = delta.seconds * onesecond
                kwhUsage = timeInHours * self.ccreadings[idx]
                trc.Trace("    " + repr(kwhUsage))
                totalUsage = kwhUsage
            elif nextReading < datehi:
                datehiReading = idx
                delta = self.ccdates[idx + 1] - self.ccdates[idx]
                trc.Trace("B : " + repr(self.ccreadings[idx]) + " for " + repr(delta.seconds) + " seconds")
                timeInHours = delta.seconds * onesecond
                kwhUsage = timeInHours * self.ccreadings[idx]
                trc.Trace("    " + repr(kwhUsage))
                totalUsage += kwhUsage
            else:
                break

        trc.Trace("dateloReading : " + repr(dateloReading))
        trc.Trace("datehiReading : " + repr(datehiReading))

        if dateloReading is None:
            dateloReading = 0

        if datehiReading is None:
            self.dlgOpen = True
            nDlg = wx.MessageDialog(self.guicallback,
                                    "Between " + datelo.strftime("%d/%m/%y %H:%M.%S") +
                                    " and " + datehi.strftime("%d/%m/%y %H:%M.%S") + "\n" +
                                    " you used 0 units of electricity \n" +
                                    " which cost you 0p",
                                    "CurrentCost",
                                    style=(wx.OK | wx.ICON_INFORMATION))
            nDlg.ShowModal()
            nDlg.Destroy()
            self.dlgOpen = False
        else:
            datehiReading += 1

            if datehiReading >= len(self.ccdates):
                datehiReading = len(self.ccdates) - 1

            trc.Trace("onselect : " + repr(datelo) + " -> " + repr(datehi))
            trc.Trace("closest matches : " + repr(self.ccdates[dateloReading]) + " -> " + repr(self.ccdates[datehiReading]))

            trc.Trace(repr(dateloReading) + " | " + repr(datehiReading))

            numUnits = "%.5f" % totalUsage

            #
            costPerUnit = self.appDatabase.RetrieveSetting("kwhcost")
            if costPerUnit is None:
                self.dlgOpen = True
                nDlg = wx.MessageDialog(self.guicallback,
                                        "Between " + self.ccdates[dateloReading].strftime("%d/%m/%y %H:%M.%S") +
                                        " and " + self.ccdates[datehiReading].strftime("%d/%m/%y %H:%M.%S") + "\n" +
                                        " you used " + numUnits + " units of electricity",
                                        "CurrentCost",
                                        style=(wx.OK | wx.ICON_INFORMATION))
                nDlg.ShowModal()
                nDlg.Destroy()
                self.dlgOpen = False
            else:
                costUnits = "%.3f" % (float(costPerUnit) * totalUsage)
                trc.Trace("cost of a unit : " + repr(float(costPerUnit)))

                self.dlgOpen = True
                nDlg = wx.MessageDialog(self.guicallback,
                                        "Between " + self.ccdates[dateloReading].strftime("%d/%m/%y %H:%M.%S") +
                                        " and " + self.ccdates[datehiReading].strftime("%d/%m/%y %H:%M.%S") + "\n" +
                                        " you used " + numUnits + " units of electricity \n" +
                                        " which cost you approximately " + costUnits + "p",
                                        "CurrentCost",
                                        style=(wx.OK | wx.ICON_INFORMATION))
                nDlg.ShowModal()
                nDlg.Destroy()
                self.dlgOpen = False

        trc.FunctionExit("currentcostlivedata :: onselect")


# a background thread used to create an MQTT connection
class MQTTUpdateThread(Thread):
    def __init__(self, mqttclienthandle, ipaddr, topic, liveagent):
        Thread.__init__(self)
        self.mqttClient = mqttclienthandle
        self.ipaddress = ipaddr
        self.topicstring = topic
        self.graphhandle = liveagent
    def run(self):
        res = self.mqttClient.EstablishConnection(self.ipaddress, 
                                                  self.topicstring, 
                                                  self.graphhandle)

# a background thread used to create a serial connection
class SerialUpdateThread(Thread):
    def __init__(self, comclienthandle, comportclass, liveagent):
        Thread.__init__(self)
        self.comClient = comclienthandle
        self.comport = comportclass
        self.graphhandle = liveagent
    def run(self):
        res = self.comClient.EstablishConnection(self.comport, 
                                                 self.graphhandle)

# a background thread used to download National Grid data
class NationalGridUpdateThread(Thread):
    disconnect = False
    ngdata = None
    def __init__(self, liveagent):
        Thread.__init__(self)
        self.graphhandle = liveagent
        self.disconnect = False
        self.ngdata = NationalGridDataSource()
    def stopUpdates(self):
        self.disconnect = True
    def run(self):
        while self.disconnect == False:
            nghtml = self.ngdata.DownloadRealtimeHTML()
            demand, freq = self.ngdata.ParseRealtimeHTML(nghtml)
            self.graphhandle.updateNationalGridGraph(demand, freq)
        


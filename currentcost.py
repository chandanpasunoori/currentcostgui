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

import os
import sys
import getopt
import logging
import urllib
import urllib2
import cookielib
import pickle 
import wx
import wx.aui
import matplotlib as mpl
import numpy as np
import datetime
import pylab
import math
import time
import datetime
import webbrowser
import serial


from googleappengine           import GoogleAppEngine
from googleappengine           import GroupData as CurrentCostGroupData
from currentcostgraphs         import Plot, PlotNotebook, TextPage
from currentcostdatafunctions  import CurrentCostDataFunctions
from currentcostvisualisations import CurrentCostVisualisations
from currentcostdb             import CurrentCostDB
from currentcostlivedata       import CurrentCostLiveData
from currentcosthistorydata    import CurrentCostHistoryData
from currentcostparser         import CurrentCostDataParser
from currentcostserialconn     import CurrentCostConnection
from tracer                    import CurrentCostTracer

from matplotlib.dates import DayLocator, HourLocator, MonthLocator, YearLocator, WeekdayLocator, DateFormatter, drange
from matplotlib.patches import Rectangle, Patch
from matplotlib.text import Text



###############################################################################
# 
# CurrentCost
# 
#  A Python application to graphically represent data received from a 
#   CurrentCost meter.
# 
#  Useful links:
#  -------------   
#     Overview of the app
#                            http://currentcost.appspot.com/static/welcome.html
#  
#     Blog posts:
#         1st version of the app              http://dalelane.co.uk/blog/?p=280
#                                             http://dalelane.co.uk/blog/?p=281
#         Re-working the app plans            http://dalelane.co.uk/blog/?p=288
#         Current version of the app          http://dalelane.co.uk/blog/?p=297
#         Seeking feedback                    http://dalelane.co.uk/blog/?p=298
#         Adding web services functions       http://dalelane.co.uk/blog/?p=305
#         Seeking testers for web services    http://dalelane.co.uk/blog/?p=307
#         Setting personal targets            http://dalelane.co.uk/blog/?p=333
#         Adding webservice showing all users http://dalelane.co.uk/blog/?p=434
#         Updating the parser                 http://dalelane.co.uk/blog/?p=456
#         Graphing National Grid data         http://dalelane.co.uk/blog/?p=469
#         Measuring costs from live graph     http://dalelane.co.uk/blog/?p=1142
# 
#     Providing support
#         http://getsatisfaction.com/dalelane/products/dalelane_currentcost_gui
#
# 
# 
#  Dale Lane (http://dalelane.co.uk/blog)
#
###############################################################################


############################################################################
# 
# OVERVIEW OF THE CODE
# ====================
# 
#   currentcost.py               - main entry function, and implements the 
#                                     GUI's menus and their actions
#   currentcostserialconn.py     - makes a serial connection to a CurrentCost
#                                     meter
#   currentcostdata.py           - represents data contained in a single 
#                                     update from a CurrentCost meter
#   currentcostparser.py         - CurrentCost XML data parser used when 
#                                     receiving data over serial connection
#   currentcostdataconvert.py    - used by XML parser to convert relative 
#                                     time descriptions into absolute
#   currentcostdatafunctions.py  - converts the relative description of usage
#                                     in a CurrentCost update into absolute
#   currentcostdb.py             - sqlite DB to persist CurrentCost usage 
#                                     data, and settings and preferences
#   currentcostgraphs.py         - matplotlib/wxPython code to implement the 
#                                     tabs that make up the GUI
#   currentcostvisualisations.py - draws bar graphs of CurrentCost data
#   currentcostmqtt.py           - downloads history data from a remote 
#                                     CurrentCost meter via MQTT
#   googleappengine.py           - gets data from a Google App Engine web 
#                                     service to show other user's data
#   currentcostlivedata.py       - draws tab to display a graph of live data
#   currentcostmqttlive.py       - downloads live data for the live graph 
#                                     from a remote CurrentCost meter via MQTT
#   currentcostcomlive.py        - downloads live data for the live graph 
#                                     from a CurrentCost meter
#   currentcosthistorydata       - implements a download manager to handle 
#                                     background downloading of history data
#   currentcostmqtthistory.py    - downloads historical data if downloading 
#                                     all updates in background via MQTT
#   currentcostcomhistory.py     - downloads historical data if downloading 
#                                     all updates in background 
#   nationalgriddata.py          - downloads live national electricity usage 
#                                     data from the National Grid realtime feed
#   tracer.py                    - very simple tracing functionality
# 
# 
############################################################################



###############################################################################
# GLOBALS
# 
#   This was initially a hacked-together few hundred lines of script, so 
#    most things were stored in globals. It grew organically, and I've yet
#    to come back and tidy these bits up. 
# 
#   These really don't need to be globals, and the intention is to complete 
#    refactoring of the code so that they are no longer stored here.
# 

#
# the overall gui
frame = None

# target lines drawn on the different graphs
targetlines = {}

# the interface that we add tabs to
plotter = None

# class for logging diagnostic info
trc = CurrentCostTracer()

# connection to the database used to store CurrentCost data
ccdb   = CurrentCostDB()

# create the parser class
myparser = CurrentCostDataParser()

# class to maintain a live data graph
livedataagent = CurrentCostLiveData()

# class to maintain history graphs
historydataagent = CurrentCostHistoryData()

# class to generate graphs
ccvis = CurrentCostVisualisations()

# class to create a serial connection to CurrentCost meters
myserialconn = CurrentCostConnection()

# temporary - these values will eventually be retrieved from a reputable source
#  such as AMEE
# in the meantime, reasonable guesses are hard-coded in the app here
#  Note: these were obtained from 
#    http://www.electricityinfo.org/supplierdataall.php?year=latest
kgCO2PerKWh = None    # all access to this value should be via getKgCO2PerKWh
CO2_BY_SUPPLIERS = { "British Gas"                : 0.368,
                     "Ecotricity"                 : 0.267,
                     "EDF Energy"                 : 0.569,
                     "Good Energy"                : 0.0,
                     "Green Energy"               : 0.129,
                     "npower"                     : 0.543,
                     "Powergen"                   : 0.377,
                     "Southern Electric"          : 0.489,  # Southern Electric is a trading name of the Scottish and Southern Energy Group
                     "Scottish & Southern Energy" : 0.489,
                     "Scottish Power"             : 0.610,
                     "Utilita"                    : 0.460,
                     "Any other UK supplier"      : 0.480 }



class MyFrame(wx.Frame):
    MENU_HISTORY     = None
    MENU_HIST_S      = None
    f1               = None
    mnuTarget        = None
    mnuTrace         = None
    MENU_SHOWKWH     = None
    MENU_SHOWGBP     = None
    MENU_SHOWCO2     = None
    MENU_TARGET      = None
    MENU_LIVE_COM    = None
    MENU_LIVE_MQTT   = None
    MENU_HIST_S_COM  = None
    MENU_HIST_S_MQTT = None
    MENU_LIVE_DEMAND = None
    MENU_LIVE_SUPPLY = None

    #
    # these are the different graphs that we draw on
    trendspg = None    # trends
    axes1    = None    # hours
    axes2    = None    # days   
    axes3    = None    # months
    axes4    = None    # average day
    axes5    = None    # average week
    liveaxes = None    # live data

    def Build_Menus(self):
        global ccdb, trc

        #
        # menu structure
        # 
        #  Download History                                         MENU_HISTORY
        #           |
        #           +---  Download once                              MENU_HIST_1
        #           |         |
        #           |         +---  Download via serial port     MENU_HIST_1_COM
        #           |         +---  Download via MQTT           MENU_HIST_1_MQTT
        #           |
        #           +---  Stay connected                             MENU_HIST_S
        #                     |
        #                     +---  Download via serial port     MENU_HIST_S_COM
        #                     +---  Download via MQTT           MENU_HIST_S_MQTT
        #                     |
        #                     +---  Redraw graphs             MENU_REDRAW_GRAPHS
        # 
        #  Show live data                                              MENU_LIVE
        #           |
        #           +---  Connect via serial port                  MENU_LIVE_COM
        #           +---  Connect via MQTT                        MENU_LIVE_MQTT
        #           |
        #           +---  Export live data                      MENU_LIVE_EXPORT
        #           |
        #           +---  Show live demand                      MENU_LIVE_DEMAND
        #           +---  Show supply vs demand                 MENU_LIVE_SUPPLY
        #           +---  Show electricity generation       MENU_LIVE_GENERATION
        # 
        # 
        # 

        MENU_HELP               = wx.NewId()
        MENU_HIST_1_COM         = wx.NewId()
        MENU_HIST_1_MQTT        = wx.NewId()
        self.MENU_HIST_S_COM    = wx.NewId()
        self.MENU_HIST_S_MQTT   = wx.NewId()
        self.MENU_LIVE_COM      = wx.NewId()
        self.MENU_LIVE_MQTT     = wx.NewId()
        self.MENU_LIVE_DEMAND   = wx.NewId()
        self.MENU_LIVE_SUPPLY   = wx.NewId()
        MENU_LIVE_GENERATION    = wx.NewId()
        MENU_REDRAW_GRAPHS      = wx.NewId()
        MENU_LOADDB             = wx.NewId()
        self.MENU_SHOWKWH       = wx.NewId()
        self.MENU_SHOWGBP       = wx.NewId()
        self.MENU_SHOWCO2       = wx.NewId()
        self.MENU_TARGET        = wx.NewId()
        MENU_EXPORT1            = wx.NewId()
        MENU_EXPORT2            = wx.NewId()
        MENU_EXPORT3            = wx.NewId()
        MENU_SYNC               = wx.NewId()
        MENU_UPLOAD             = wx.NewId()
        MENU_DNLOAD             = wx.NewId()
        MENU_ACCNT              = wx.NewId()
        MENU_PROFILE            = wx.NewId()
        MENU_COMPARE            = wx.NewId()
        MENU_UPDATES            = wx.NewId()
        MENU_BUGREPT            = wx.NewId()
        MENU_MANUAL             = wx.NewId()
        MENU_MATPLOT            = wx.NewId()
        MENU_TRACE              = wx.NewId()
        MENU_HELPDOC            = wx.NewId()
        MENU_LIVE_EXPORT        = wx.NewId()

        menuBar = wx.MenuBar()

        self.MENU_HISTORY = wx.Menu()
        self.MENU_HIST_1  = wx.Menu()
        self.MENU_HIST_1.Append(MENU_HIST_1_COM,  "Download via serial port", "Connect to a CurrentCost meter and download CurrentCost history data")
        self.MENU_HIST_1.Append(MENU_HIST_1_MQTT, "Download via MQTT",        "Receive CurrentCost history data from an MQTT-compatible message broker")
        self.MENU_HIST_S  = wx.Menu()
        self.MENU_HIST_S.Append(self.MENU_HIST_S_COM,  "Download via serial port", "Connect to a CurrentCost meter and download CurrentCost history data", kind=wx.ITEM_CHECK)
        self.MENU_HIST_S.Append(self.MENU_HIST_S_MQTT, "Download via MQTT",        "Receive CurrentCost history data from an MQTT-compatible message broker", kind=wx.ITEM_CHECK)
        self.MENU_HIST_S.AppendSeparator()
        self.MENU_HIST_S.Append(MENU_REDRAW_GRAPHS, "Redraw graphs", "Redraw the history graphs based on current data store")

        self.MENU_LIVE = wx.Menu()        
        self.MENU_LIVE.Append(self.MENU_LIVE_COM,  "Connect via serial port", "Connect to a CurrentCost meter and display live CurrentCost updates", kind=wx.ITEM_CHECK)
        self.MENU_LIVE.Append(self.MENU_LIVE_MQTT, "Connect via MQTT",        "Receive live CurrentCost updates from an MQTT-compatible message broker", kind=wx.ITEM_CHECK)
        self.MENU_LIVE.AppendSeparator()
        self.MENU_LIVE.Append(MENU_LIVE_EXPORT, "Export live data to CSV...", "Export live CurrentCost data from this session to a CSV spreadsheet file")
        self.MENU_LIVE.AppendSeparator()
        self.MENU_LIVE.Append(self.MENU_LIVE_DEMAND, "National electricity demand",    "Show live data from the National Grid website showing national electricity demand", kind=wx.ITEM_CHECK)
        self.MENU_LIVE.Append(self.MENU_LIVE_SUPPLY, "National Grid supply vs demand", "Show live data from the National Grid website from the grid frequency", kind=wx.ITEM_CHECK)
        self.MENU_LIVE.Append(MENU_LIVE_GENERATION, "National electricity generation", "Show live electricity usage divided by the source of generated power")

        self.f1 = wx.Menu()
        self.f1.Append(self.MENU_SHOWKWH, "Display kWH", "Show kWH on CurrentCost graphs", kind=wx.ITEM_CHECK)
        self.f1.Append(self.MENU_SHOWGBP, "Display GBP", "Show GBP on CurrentCost graphs", kind=wx.ITEM_CHECK)
        self.f1.Append(self.MENU_SHOWCO2, "Display CO2", "Show CO2 on CurrentCost graphs", kind=wx.ITEM_CHECK)
        self.f1.Check(self.MENU_SHOWKWH, True)
        self.f1.Check(self.MENU_SHOWGBP, False)
        self.f1.Check(self.MENU_SHOWCO2, False)
        self.f1.AppendSeparator()
        self.mnuTarget = self.f1.Append(self.MENU_TARGET,  "Set personal target", "Set a usage target", kind=wx.ITEM_CHECK)
        self.f1.Check(self.MENU_TARGET, False)

        f2 = wx.Menu()
        f2.Append(MENU_EXPORT1, "Export hours to CSV...", "Export stored two-hourly CurrentCost data to a CSV spreadsheet file")
        f2.Append(MENU_EXPORT2, "Export days to CSV...", "Export stored daily CurrentCost data to a CSV spreadsheet file")
        f2.Append(MENU_EXPORT3, "Export months to CSV...", "Export stored monthly CurrentCost data to a CSV spreadsheet file")
        f2.AppendSeparator()
        f2.Append(MENU_MANUAL,  "Import XML", "Manually import XML CurrentCost data")

        f3 = wx.Menu()
        #f3.Append(MENU_UPLOAD,  "Upload data to web...", "Upload CurrentCost data to the web")
        #f3.Append(MENU_DNLOAD,  "Download data from web...", "Download CurrentCost data from your groups from the web")
        f3.Append(MENU_SYNC,  "Sync with web...", "Synchronise your CurrentCost data with the web to see how you compare with your groups")
        f3.AppendSeparator()
        f3.Append(MENU_COMPARE, "Compare friends...", "Compare CurrentCost averages of up to four users")
        f3.AppendSeparator()
        f3.Append(MENU_ACCNT,   "Create account...", "Create an account online to store and access CurrentCost data")
        f3.Append(MENU_PROFILE, "Manage profile...", "Manage online profile")

        f4 = wx.Menu()
        f4.Append(MENU_HELP, "About",  "Show basic info about this app")
        f4.AppendSeparator()
        f4.Append(MENU_UPDATES, "Check for updates", "Check that the desktop application is up-to-date")
        f4.Append(MENU_BUGREPT, "Report a bug", "Please use getsatisfaction to report bugs, ask questions, or request features")
        f4.AppendSeparator()
        f4.Append(MENU_MATPLOT, "What do the toolbar buttons do?", "See documentation on the pan and zoom controls")
        f4.Append(MENU_HELPDOC, "General help", "See general documentation about the app")
        f4.AppendSeparator()
        self.mnuTrace = f4.Append(MENU_TRACE, "Collect diagnostics", "Enable tracing for the developer", kind=wx.ITEM_CHECK)
        self.mnuTrace.Check(check=trc.IsTraceEnabled())

        self.MENU_HISTORY.AppendMenu(-1, "Download once",  self.MENU_HIST_1)
        self.MENU_HISTORY.AppendMenu(-1, "Stay connected", self.MENU_HIST_S)

        menuBar.Append(self.MENU_HISTORY, "Download history")
        menuBar.Append(self.MENU_LIVE,    "Show live data")
        menuBar.Append(self.f1,           "Data")
        menuBar.Append(f2,                "Export history")
        menuBar.Append(f3,                "Web")
        menuBar.Append(f4,                "Help")

        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU, self.onAbout,              id=MENU_HELP)
        self.Bind(wx.EVT_MENU, self.onDownloadOnceSerial, id=MENU_HIST_1_COM)
        self.Bind(wx.EVT_MENU, self.onDownloadOnceMQTT,   id=MENU_HIST_1_MQTT)
        self.Bind(wx.EVT_MENU, self.onDownloadAllSerial,  id=self.MENU_HIST_S_COM)
        self.Bind(wx.EVT_MENU, self.onDownloadAllMQTT,    id=self.MENU_HIST_S_MQTT)
        self.Bind(wx.EVT_MENU, self.onLiveConnectSerial,  id=self.MENU_LIVE_COM)
        self.Bind(wx.EVT_MENU, self.onLiveConnectMQTT,    id=self.MENU_LIVE_MQTT)
        self.Bind(wx.EVT_MENU, self.onRedrawGraphs,       id=MENU_REDRAW_GRAPHS)
        self.Bind(wx.EVT_MENU, self.onExportHours,        id=MENU_EXPORT1)
        self.Bind(wx.EVT_MENU, self.onExportDays,         id=MENU_EXPORT2)
        self.Bind(wx.EVT_MENU, self.onExportMonths,       id=MENU_EXPORT3)
        self.Bind(wx.EVT_MENU, self.onExportLive,         id=MENU_LIVE_EXPORT)
        self.Bind(wx.EVT_MENU, self.onUploadData,         id=MENU_UPLOAD)
        self.Bind(wx.EVT_MENU, self.onDownloadData,       id=MENU_DNLOAD)
        self.Bind(wx.EVT_MENU, self.onSyncData,           id=MENU_SYNC)
        self.Bind(wx.EVT_MENU, self.onCompareUsers,       id=MENU_COMPARE)
        self.Bind(wx.EVT_MENU, self.onManageAcct,         id=MENU_ACCNT)
        self.Bind(wx.EVT_MENU, self.onManageAcct,         id=MENU_PROFILE)
        self.Bind(wx.EVT_MENU, self.onUpdatesCheck,       id=MENU_UPDATES)
        self.Bind(wx.EVT_MENU, self.onShowWebsite,        id=MENU_BUGREPT)
        self.Bind(wx.EVT_MENU, self.onShowKWH,            id=self.MENU_SHOWKWH)
        self.Bind(wx.EVT_MENU, self.onShowGBP,            id=self.MENU_SHOWGBP)
        self.Bind(wx.EVT_MENU, self.onShowCO2,            id=self.MENU_SHOWCO2)
        self.Bind(wx.EVT_MENU, self.onSetUsageTarget,     id=self.MENU_TARGET)
        self.Bind(wx.EVT_MENU, self.getDataFromXML,       id=MENU_MANUAL)
        self.Bind(wx.EVT_MENU, self.openMatplotlibUrl,    id=MENU_MATPLOT)
        self.Bind(wx.EVT_MENU, self.openHelpUrl,          id=MENU_HELPDOC)
        self.Bind(wx.EVT_MENU, self.onNationalGridDemand, id=self.MENU_LIVE_DEMAND)
        self.Bind(wx.EVT_MENU, self.onNationalGridFreq,   id=self.MENU_LIVE_SUPPLY)
        self.Bind(wx.EVT_MENU, self.onNationalGridGen,    id=MENU_LIVE_GENERATION)
        self.Bind(wx.EVT_MENU, self.onToggleTrace,        id=MENU_TRACE)

        self.Bind(wx.EVT_CLOSE, self.OnClose)



    # added this to handle when the application is closed because we need 
    #  to disconnect any open connections first
    def OnClose(self, event):
        global ccdb

        progDlg = wx.ProgressDialog ('CurrentCost', 
                                     'Shutting down...', 
                                     maximum = 4, 
                                     style=wx.PD_AUTO_HIDE)

        progDlg.Update(1)
        ccdb.CloseDB()

        progDlg.Update(2)
        livedataagent.disconnect()

        progDlg.Update(3)
        historydataagent.disconnect()

        progDlg.Update(4)
        progDlg.Destroy()
        self.Destroy()


    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, size=(1024, 768))
        self.Build_Menus()
        self.statusBar = wx.StatusBar(self, -1)
        self.statusBar.SetFieldsCount(1)
        self.SetStatusBar(self.statusBar)
        iconfile = 'electricity.ico'
        icon1 = wx.Icon(iconfile, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon1)


    # display info about the app
    def onAbout (self, event):
        info = wx.AboutDialogInfo()
        info.SetIcon(wx.Icon('electricity.ico', wx.BITMAP_TYPE_ICO))
        info.SetName('CurrentCost')
        info.Developers = ['Dale Lane']
        info.Description = "Draws interactive graphs using the data from a CurrentCost electricity meter"
        info.Version = "0.9.30"
        info.WebSite = ("http://code.google.com/p/currentcostgui/", "http://code.google.com/p/currentcostgui/")
        wx.AboutBox(info)

    # helper function to update the status bar
    def UpdateStatusBar(self, event):
        global ccvis
        if event.inaxes:
            x, y = event.xdata, event.ydata
            statustext = "%.2f " + ccvis.graphunitslabel
            self.statusBar.SetStatusText((statustext % y), 0)

    # 
    def onToggleTrace(self, event):
        global trc
        trc.FunctionEntry("onToggleTrace")
        trc.EnableTrace(self.mnuTrace.IsChecked())
        if self.mnuTrace.IsChecked() == True:
            trc.InitialiseTraceFile()

    #################
    # 
    # web links - launch web pages
    # 
    def onManageAcct(self, event):
        webbrowser.open_new_tab('http://currentcost.appspot.com/profile')

    def onShowWebsite(self, event):
        webbrowser.open_new_tab('http://getsatisfaction.com/dalelane/products/dalelane_currentcost_gui')

    def openMatplotlibUrl(self, event):
        webbrowser.open_new_tab('http://matplotlib.sourceforge.net/users/navigation_toolbar.html')

    def openHelpUrl(self, event):
        webbrowser.open_new_tab('http://code.google.com/p/currentcostgui/')


    #####################
    # 
    # web services functions - connect to Google App Engine
    # 

    #
    # check with the web service for updates to the client

    def onUpdatesCheck(self, event):
        gae = GoogleAppEngine()
        latestversion = gae.GetDesktopVersion()

        if latestversion == "unknown":
            confdlg = wx.MessageDialog(self,
                                       "Unable to connect to CurrentCost web service",
                                       'CurrentCost', 
                                       style=(wx.OK | wx.ICON_EXCLAMATION))
            result = confdlg.ShowModal()        
            confdlg.Destroy()
        elif latestversion != "0.9.30":
            confdlg = wx.MessageDialog(self,
                                       "A newer version of this application (" + latestversion + ") is available.\n\n"
                                       "Download now?",
                                       'CurrentCost', 
                                       style=(wx.YES | wx.NO | wx.ICON_EXCLAMATION))
            result = confdlg.ShowModal()
            if result == wx.ID_YES:
                webbrowser.open_new_tab('http://code.google.com/p/currentcostgui/')
            confdlg.Destroy()
        else:
            confdlg = wx.MessageDialog(self,
                                       "Your version of the application is up to date.",
                                       'CurrentCost', 
                                       style=(wx.OK | wx.ICON_INFORMATION))
            result = confdlg.ShowModal()        
            confdlg.Destroy()


    # wrapper for upload then download
    def onSyncData(self, event):
        gae = GoogleAppEngine()
        if self.uploadData(gae) == True:
            self.downloadData(gae)

    #
    # download group averages from Google
    
    def onDownloadData(self, event):
        gae = GoogleAppEngine()
        self.downloadData(gae)

    def downloadData(self, gae):
        global plotter, ccdb, ccvis, trc
        trc.FunctionEntry("downloadData")

        hourDataCollection = ccdb.GetHourDataCollection()
        dayDataCollection = ccdb.GetDayDataCollection()

        ccdata = CurrentCostDataFunctions()
        averageDayData = ccdata.CalculateAverageDay(hourDataCollection)
        averageWeekData = ccdata.CalculateAverageWeek(dayDataCollection)

        groupgoogledata, daygoogledata = gae.DownloadCurrentCostDataFromGoogle(self, ccdb)
        trc.Trace("found " + str(len(groupgoogledata)) + " groups on Google")
        if groupgoogledata:
            for group in groupgoogledata:
                tabname = groupgoogledata[group].groupname + " : week"
                plotter.deletepage(tabname)
                groupdataaxes = plotter.add(tabname).gca()
                ccvis.PlotGroupWeekData(dayDataCollection, averageWeekData, groupgoogledata[group], groupdataaxes)
        if daygoogledata:
            tabname = 'everyone : week'
            plotter.deletepage(tabname)
            dayaxes = plotter.add(tabname).gca()            
            ccvis.PlotDailyScatterGraph(dayaxes, averageWeekData, daygoogledata)

        trc.FunctionExit("downloadData")

    #
    # upload user data to Google
    
    def onUploadData(self, event):
        gae = GoogleAppEngine()
        self.uploadData(gae)

    def uploadData(self, gae):
        global ccdb

        confdlg = wx.MessageDialog(self,
                                   "This will upload your historical electricity "
                                   "usage data to a publicly-accessible web server. \n\n"
                                   "Every effort will be made to ensure that this "
                                   "data will only be visible in anonymised forms\n "
                                   "and not as individual electricity records "
                                   "identified with specific users. \n\n"
                                   "However, if you have any concerns about this "
                                   "information being public, please click NO now.",
                                   'Are you sure?', 
                                   style=(wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION))
        result = confdlg.ShowModal()        
        confdlg.Destroy()

        if result != wx.ID_YES:
            return

        return gae.UploadCurrentCostDataToGoogle(self, ccdb)


    #
    #  display average data for specific users

    def onCompareUsers(self, event):

        global ccdb, ccvis

        userEntryDialog = wx.TextEntryDialog(self, 
                                             'Enter up to four usernames of friends to compare\n (one username per line):',
                                             'CurrentCost',
                                             '',
                                             wx.TE_MULTILINE | wx.OK | wx.CANCEL )
        result = userEntryDialog.ShowModal()

        users = userEntryDialog.GetValue().split('\n')
        userEntryDialog.Destroy()

        if result != wx.ID_OK:
            return


        progDlg = wx.ProgressDialog ('CurrentCost', 
                                     'Comparing electricity usage with named friends', 
                                     maximum = 6, 
                                     style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)

        (tocontinue, toskip) = progDlg.Update(1, 'Preparing visualisations class')
        if tocontinue == False:
            progDlg.Update(6, "Cancelled")
            progDlg.Destroy()
            return

        progDlg.Update(2, 'Preparing Google communications class')
        gae = GoogleAppEngine()

        verifiedusers = []

        (tocontinue, toskip) = progDlg.Update(3, 'Verifying that requested users have granted access')
        if tocontinue == False:
            progDlg.Update(6, "Cancelled")
            progDlg.Destroy()
            return

        for user in users:
            (tocontinue, toskip) = progDlg.Update(3, 'Verifying that ' + user + ' has granted access')
            if tocontinue == False:
                progDlg.Update(6, "Cancelled")
                progDlg.Destroy()
                return
            
            res = gae.VerifyPermissionsForUser(self, ccdb, user)
            if res == None:
                errdlg = wx.MessageDialog(self,
                                          user + ' is not a recognised CurrentCost username. ',
                                          'CurrentCost', 
                                          style=(wx.OK | wx.ICON_ERROR))
                errdlg.ShowModal()        
                errdlg.Destroy()
            elif res == False:
                errdlg = wx.MessageDialog(self,
                                          user + ' has not confirmed that you are '
                                          'allowed to see their CurrentCost data. '
                                          '\n\n'
                                          'Please ask them to visit '
                                          'http://currentcost.appspot.com/friends '
                                          'and add your username.',
                                          'CurrentCost', 
                                          style=(wx.OK | wx.ICON_INFORMATION))
                errdlg.ShowModal()        
                errdlg.Destroy()
            else:
                verifiedusers.append(user)
        
        # verifiedusers is a list of usernames
        #  we will ignore everything after the first four

        if len(verifiedusers) == 0:
            progDlg.Update(6, "Nothing to display")
            progDlg.Destroy()
            return
            

        maxrange = 4
        if len(verifiedusers) < 4:
            maxrange = len(verifiedusers)

        # we have a list of names to download data for

        (tocontinue, toskip) = progDlg.Update(4, 'Downloading usage for friends')
        if tocontinue == False:
            progDlg.Update(6, "Cancelled")
            progDlg.Destroy()
            return

        graphdata = {}
        for i in range(0, maxrange):
            (tocontinue, toskip) = progDlg.Update(5, 'Downloading ' + verifiedusers[i] + '\'s data')
            if tocontinue == False:
                progDlg.Update(6, "Cancelled")
                progDlg.Destroy()
                return
            graphdata[verifiedusers[i]] = gae.DownloadCurrentCostUserDataFromGoogle(verifiedusers[i])

            # tell the user if we wont be displaying data for a requested user
            datachk = len(graphdata[verifiedusers[i]])
            if datachk == 0:
                errdlg = wx.MessageDialog(self,
                                          verifiedusers[i] + ' has not uploaded data to the CurrentCost site',
                                          'CurrentCost', 
                                          style=(wx.OK | wx.ICON_ERROR))
                errdlg.ShowModal()        
                errdlg.Destroy()
            elif datachk < 7:
                errdlg = wx.MessageDialog(self,
                                          'Averages could only obtained for ' + str(datachk) + ' days from ' + verifiedusers[i],
                                          'CurrentCost', 
                                          style=(wx.OK | wx.ICON_INFORMATION))
                errdlg.ShowModal()        
                errdlg.Destroy()

                

        progDlg.Update(5, 'Drawing graph')
        tabname = "comparing friends"
        plotter.deletepage(tabname)
        friendaxes = plotter.add(tabname).gca()
        ccvis.PlotFriendsWeekData(friendaxes, graphdata)

        progDlg.Update(6, 'Complete')
        progDlg.Destroy()


            



    #####################
    # 
    # export functions - export to CSV

    def onExportHours(self, event):
        global ccdb
        hourDataCollection = ccdb.GetHourDataCollection()
        dialog = wx.FileDialog( None, style = wx.SAVE, wildcard="Comma-separated values files (*.csv)|*.csv")
        if dialog.ShowModal() == wx.ID_OK:
            ccdatafn = CurrentCostDataFunctions()
            ccdatafn.ExportHourData(dialog.GetPath(), hourDataCollection)
            self.SetStatusText("CurrentCost data exported to " + dialog.GetPath())
        dialog.Destroy()

    def onExportDays(self, event):
        global ccdb
        dayDataCollection = ccdb.GetDayDataCollection()
        dialog = wx.FileDialog( None, style = wx.SAVE, wildcard="Comma-separated values files (*.csv)|*.csv")
        if dialog.ShowModal() == wx.ID_OK:
            ccdatafn = CurrentCostDataFunctions()
            ccdatafn.ExportDateData(dialog.GetPath(), dayDataCollection)
            self.SetStatusText("CurrentCost data exported to " + dialog.GetPath())
        dialog.Destroy()

    def onExportMonths(self, event):
        global ccdb
        monthDataCollection = ccdb.GetMonthDataCollection()
        dialog = wx.FileDialog( None, style = wx.SAVE, wildcard="Comma-separated values files (*.csv)|*.csv")
        if dialog.ShowModal() == wx.ID_OK:
            ccdatafn = CurrentCostDataFunctions()
            ccdatafn.ExportDateData(dialog.GetPath(), monthDataCollection)
            self.SetStatusText("CurrentCost data exported to " + dialog.GetPath())
        dialog.Destroy()

    def onExportLive(self, event):
        dialog = wx.FileDialog( None, style = wx.SAVE, wildcard="Comma-separated values files (*.csv)|*.csv")
        if dialog.ShowModal() == wx.ID_OK:
            livedataagent.ExportLiveData(dialog.GetPath())
            self.SetStatusText("CurrentCost data exported to " + dialog.GetPath())
        dialog.Destroy()


    #
    # connect to a CurrentCost meter directly
    #  
    #  if data is successfully retrieved, then redraw the graphs using the new
    #   data
    # 
    def onDownloadOnceSerial (self, event):
        global ccdb, livedataagent, myserialconn, trc

        trc.FunctionEntry("onDownloadOnceSerial")

        # if already connected, we do not need to connect now
        reuseconnection = myserialconn.isConnected()

        if reuseconnection == True:
            trc.Trace("reusing existing serial connection")
            dialog = wx.ProgressDialog ('CurrentCost', 
                                        'Connecting to local CurrentCost meter using serial connection', 
                                        maximum = 11, 
                                        style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
            if getDataFromCurrentCostMeter("", dialog) == True:
                drawMyGraphs(self, dialog, False)
            dialog.Destroy()
        else:
            trc.Trace("creating a new serial connection")
            dlg = wx.TextEntryDialog(self, 'Specify the COM port to connect to:','CurrentCost')
            lastcom = ccdb.RetrieveSetting("comport")
            if lastcom:
                trc.Trace("last used serial port: " + lastcom)
                dlg.SetValue(lastcom)
            if dlg.ShowModal() == wx.ID_OK:
                newcom = dlg.GetValue()
                if lastcom != newcom:
                    trc.Trace("user entered new serial port setting: " + newcom)
                    ccdb.StoreSetting("comport", newcom)
                dialog = wx.ProgressDialog ('CurrentCost', 
                                            'Connecting to local CurrentCost meter using serial connection', 
                                            maximum = 11, 
                                            style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
                if getDataFromCurrentCostMeter(dlg.GetValue(), dialog) == True:
                    drawMyGraphs(self, dialog, False)
                dialog.Destroy()
            dlg.Destroy()

        trc.FunctionExit("onDownloadOnceSerial")

    #
    # connect to a CurrentCost meter via MQTT
    #  
    #  if data is successfully retrieved, then redraw the graphs using the new
    #   data
    # 
    def onDownloadOnceMQTT (self, event):
        global ccdb, mqttupd

        if self.IsMQTTSupportAvailable():
            # used to provide an MQTT connection to a remote CurrentCost meter
            # import the necessary third-party code to provide MQTT support
            mqttClientModule = __import__("currentcostmqtt")
            mqttClient = mqttClientModule.CurrentCostMQTTConnection()

            #
            # get information from the user required to establish the connection
            #  prefill with setting from database if possible
            #
    
            # IP address
    
            dlg = wx.TextEntryDialog(self, 
                                     'Specify the IP address or hostname of a message broker to connect to:',
                                     'CurrentCost')
            lastipaddr = ccdb.RetrieveSetting("mqttipaddress")
            if lastipaddr:
                dlg.SetValue(lastipaddr)
            else:
                dlg.SetValue('204.146.213.96')
            if dlg.ShowModal() != wx.ID_OK:
                return False
            ipaddr = dlg.GetValue()
            if lastipaddr != ipaddr:
                ccdb.StoreSetting("mqttipaddress", ipaddr)
            dlg.Destroy()
    
            # topic string
    
            dlg = wx.TextEntryDialog(self, 
                                     'Specify the topic string to subscribe to:',
                                     'CurrentCost')
            lasttopicstring = ccdb.RetrieveSetting("mqtttopicstring")
            if lasttopicstring:
                dlg.SetValue(lasttopicstring)
            else:
                dlg.SetValue('PowerMeter/history/YourUserNameHere')
            if dlg.ShowModal() != wx.ID_OK:
                return False
            topicString = dlg.GetValue()
            if lasttopicstring != topicString:
                ccdb.StoreSetting("mqtttopicstring", topicString)
            dlg.Destroy()


            mqttupd = None
            maxitems = 11
            dialog = wx.ProgressDialog ('CurrentCost', 
                                        'Connecting to message broker to receive published CurrentCost data', 
                                        maximum = maxitems, 
                                        style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)

            if mqttClient.EstablishConnection(self, dialog, maxitems, ipaddr, topicString) == True:
                dialog.Update(6, "Subscribed to history feed. Waiting for data")

                while mqttupd == None:
                    time.sleep(1)
                    (tocontinue, toskip) = dialog.Update(7, "Waiting for data")
                    if tocontinue == False:
                        dialog.Destroy()
                        return

                dialog.Update(8, "Received data from message broker")

                ccfuncs = CurrentCostDataFunctions()

                dialog.Update(9, "Parsing data from message broker")
                ccfuncs.ParseCurrentCostXML(ccdb, mqttupd)

                dialog.Update(10, "Drawing graphs")
                drawMyGraphs(self, dialog, False)

                dialog.Update(maxitems, "Complete")

            dialog.Destroy()
        else:
            dlg = wx.MessageDialog(self,
                                   "Connecting via MQTT requires the use of a third-party module. "
                                   "This module is not present.\n\n"
                                   "Please copy the MQTT library to the directory where the CurrentCost app is stored then try this again",
                                   'CurrentCost', 
                                   style=(wx.OK | wx.ICON_EXCLAMATION))
            dlg.ShowModal()        
            dlg.Destroy()



    def onMQTTSubscribeCallback (self, newccupdate):
        global mqttupd
        mqttupd = newccupdate


    #
    # MQTT support requires the use of a third-party Python module, which I 
    #  am not able to re-distribute.
    # 
    # The user is required to obtain this module for themselves. This function
    #  checks for the presence of this module.
    # 
    def IsMQTTSupportAvailable(self):
        # location of the executable. we need a third-party MQTT module to 
        #  provide the ability to subscribe to an MQTT topic, and we want to 
        #  look for this in the same directory where the application is stored
        currentdir = sys.path[0]

        # special case : py2exe-compiled apps store the zip in a different place
        if os.path.basename(currentdir) == "library.zip":
            currentdir = os.path.join(currentdir, "..")

        # location of the MQTT module
        pythonmodule = os.path.join(currentdir, "mqttClient.py")
    
        # check if the MQTT client Python module file exists
        #  if not, then it is likely that we do not have MQTT support
        return os.path.isfile(pythonmodule)



    #
    # manually enter XML for parsing - for test use only
    
    def getDataFromXML(self, event):
        global myparser, ccdb, trc
        trc.FunctionEntry("getDataFromXML")
        # 
        line = ""
        dlg = wx.TextEntryDialog(self, 'Enter the XML:', 'CurrentCost')
        if dlg.ShowModal() == wx.ID_OK:
            line = dlg.GetValue()
        dlg.Destroy()

        trc.Trace("xml entered by user")
        trc.Trace(line)

        # try to parse the XML
        currentcoststruct = myparser.parseCurrentCostXML(line)

        if currentcoststruct == None:
            # something wrong with the line of xml we received
            trc.Error('Received invalid data')
            trc.FunctionExit("getDataFromXML")
            return False
        else:
            trc.Trace("storing parsed data")
            # store the CurrentCost data in the datastore
            myparser.storeTimedCurrentCostData(ccdb)

        # 
        trc.FunctionExit("getDataFromXML")
        return True


    ####################
    # 
    # download 'all' - download the history until told to stop
    # 
    # 

    # used to call onRedrawGraphs from a non-GUI thread
    def requestRedrawGraphs(self):
        wx.CallAfter(self.onRedrawGraphs, None)

    # redraw the graphs
    #
    # this is a temporary kludge - when using 'download all' to keep an open 
    #  connection, we don't know when to automatically redraw the graphs
    # 
    # so we make the user do it
    def onRedrawGraphs(self, event):
        global trc
        trc.FunctionEntry("onRedrawGraphs")
        maxitems = 11
        dialog = wx.ProgressDialog ('CurrentCost', 
                                    'Refreshing CurrentCost graphs', 
                                    maximum = maxitems, 
                                    style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
        dialog.Update(10, "Drawing graphs")
        drawMyGraphs(self, dialog, False)
        dialog.Update(maxitems, "Complete")
        dialog.Destroy()
        trc.FunctionExit("onRedrawGraphs")


    # connecting directly 
    def onDownloadAllSerial (self, event):
        global historydataagent, ccdb, myserialconn, trc
        trc.FunctionEntry("onDownloadAllSerial")

        if historydataagent.connectionType == historydataagent.CONNECTION_SERIAL:
            trc.Trace("Active history data agent using serial connection")
            # disconnect
            historydataagent.disconnect()
            # update the GUI to show what the user has selected
            self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
            self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
            #self.stopBackgroundGraphing()
            trc.FunctionExit("onDownloadAllSerial")
            return

        if historydataagent.connectionType == historydataagent.CONNECTION_MQTT:
            trc.Trace("Active history data agent using MQTT connection")
            # disconnect any existing connection
            historydataagent.disconnect()


        # if already connected, we do not need to connect now
        reuseconnection = myserialconn.isConnected()

        if reuseconnection == True:
            trc.Trace("reusing an existing serial connection")
            # create a data connection
            historydataagent.connect(self, ccdb.dbLocation,
                                     historydataagent.CONNECTION_SERIAL, 
                                     None, None, # arguments used by CONNECTION_MQTT
                                     myserialconn)
            
            # update the GUI to show what the user has selected
            self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  True)
            self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
            #self.startBackgroundGraphing()
        else:
            trc.Trace("creating a new serial connection")
            # serial port not already connected, so we need to connect now
            #
            # get information from the user required to establish the connection
            #  prefill with setting from database if possible
            #
            dlg = wx.TextEntryDialog(self, 'Specify the COM port to connect to:','CurrentCost')
            lastcom = ccdb.RetrieveSetting("comport")
            if lastcom:
                dlg.SetValue(lastcom)
                trc.Trace("last used COM port: " + lastcom)
            if dlg.ShowModal() == wx.ID_OK:
                newcom = dlg.GetValue()
                trc.Trace("user entered COM port value: " + newcom)
                if lastcom != newcom:
                    ccdb.StoreSetting("comport", newcom)
    
                try:
                    # connect to the CurrentCost meter
                    #
                    # we *hope* that the serialconn class will automatically handle what
                    # connection settings (other than COM port number) are required for the
                    # model of CurrentCost meter we are using
                    #
                    # the serialconn class does not handle serial exceptions - we need to
                    # catch and handle these ourselves
                    # (the only exception to this is that it will close the connection
                    #  in the event of an error, so we do not need to do this explicitly)
                    trc.Trace("connecting to serial port")
                    myserialconn.connect(newcom)
                except serial.SerialException, msg:
                    trc.Error("Failed to connect to CurrentCost meter")
                    trc.Error("SerialException: " + str(msg))
                    errdlg = wx.MessageDialog(None,
                                              'Serial Exception: ' + str(msg),
                                              'Failed to connect to CurrentCost meter',
                                              style=(wx.OK | wx.ICON_EXCLAMATION))
                    errdlg.ShowModal()
                    errdlg.Destroy()
                    self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                    self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                    #self.stopBackgroundGraphing()
                    trc.FunctionExit("onDownloadAllSerial")
                    return False
                except Exception, err:
                    trc.Error("Failed to connect to CurrentCost meter")
                    trc.Error(str(err))
                    errdlg = wx.MessageDialog(None,
                                              'CurrentCost',
                                              'Failed to connect to CurrentCost meter',
                                              style=(wx.OK | wx.ICON_EXCLAMATION))
                    errdlg.ShowModal()
                    errdlg.Destroy()
                    self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                    self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                    #self.stopBackgroundGraphing()
                    trc.FunctionExit("onDownloadAllSerial")
                    return False
    
                # create a data connection
                historydataagent.connect(self, ccdb.dbLocation,
                                         historydataagent.CONNECTION_SERIAL, 
                                         None, None, # arguments used by CONNECTION_MQTT
                                         myserialconn)
                
                # update the GUI to show what the user has selected
                self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  True)
                self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                #self.startBackgroundGraphing()
            else:
                # update the GUI to show that the user has cancelled
                self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                #self.stopBackgroundGraphing()
            dlg.Destroy()

        trc.FunctionExit("onDownloadAllSerial")


    # connecting via MQTT
    def onDownloadAllMQTT (self, event):
        global historydataagent, ccdb

        if self.IsMQTTSupportAvailable():
            if historydataagent.connectionType == historydataagent.CONNECTION_MQTT:
                # disconnect
                historydataagent.disconnect()
                # update the GUI to show what the user has selected
                self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                self.stopBackgroundGraphing()
                return

            if historydataagent.connectionType == historydataagent.CONNECTION_SERIAL:
                # disconnect any existing connection
                historydataagent.disconnect()

            #
            # get information from the user required to establish the connection
            #  prefill with setting from database if possible
            #
    
            # IP address
    
            dlg = wx.TextEntryDialog(self, 
                                     'Specify the IP address or hostname of a message broker to connect to:',
                                     'CurrentCost')
            lastipaddr = ccdb.RetrieveSetting("mqttipaddress")
            if lastipaddr:
                dlg.SetValue(lastipaddr)
            else:
                dlg.SetValue('204.146.213.96')
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                self.stopBackgroundGraphing()
                return False
            ipaddr = dlg.GetValue()
            if lastipaddr != ipaddr:
                ccdb.StoreSetting("mqttipaddress", ipaddr)
            dlg.Destroy()
    
            # topic string

            dlg = wx.TextEntryDialog(self, 
                                     'Specify the topic string to subscribe to:',
                                     'CurrentCost')
            lasttopicstring = ccdb.RetrieveSetting("mqtttopicstring")
            if lasttopicstring:
                dlg.SetValue(lasttopicstring)
            else:
                dlg.SetValue('PowerMeter/history/YourUserNameHere')
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
                self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
                self.stopBackgroundGraphing()
                return False
            topicString = dlg.GetValue()
            if lasttopicstring != topicString:
                ccdb.StoreSetting("mqtttopicstring", topicString)
            dlg.Destroy()

            # create a new connection
            historydataagent.connect(self, ccdb.dbLocation,
                                     historydataagent.CONNECTION_MQTT, 
                                     ipaddr, topicString,
                                     None)  # argument used by CONNECTION_SERIAL
            
            # update the GUI to show what the user has selected
            self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
            self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, True)
            self.startBackgroundGraphing()
        else:
            dlg = wx.MessageDialog(self,
                                   "Connecting via MQTT requires the use of a third-party module. "
                                   "This module is not present.\n\n"
                                   "Please copy the MQTT library to the directory where the CurrentCost app is stored then try this again",
                                   'CurrentCost', 
                                   style=(wx.OK | wx.ICON_EXCLAMATION))
            dlg.ShowModal()        
            dlg.Destroy()

            # update the GUI to show what the user has selected
            self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
            self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
            self.stopBackgroundGraphing()

        return


    def displayHistoryConnectFailure(self, message):
        self.MENU_HIST_S.Check(self.MENU_HIST_S_COM,  False)
        self.MENU_HIST_S.Check(self.MENU_HIST_S_MQTT, False)
        errdlg = wx.MessageDialog(self,
                                  message,
                                  'CurrentCost - stay connected',
                                  style=(wx.OK | wx.ICON_EXCLAMATION))
        result = errdlg.ShowModal()
        errdlg.Destroy()
        self.stopBackgroundGraphing()


    def startBackgroundGraphing(self):
        dlg = wx.MessageDialog(self,
                               "Data will continue to be downloaded from the "
                               "CurrentCost meter in the background.\n\n"
                               "However, graphs will not be updated with the new "
                               "data until you restart the app, or manually \n"
                               "refresh the graphs using 'Download History' -> "
                               "'Stay connected' -> 'Redraw graphs'\n\n"
                               "This is a temporary limitation - future versions "
                               "of the application will update graphs automatically",
                               'CurrentCost',
                               style=(wx.OK | wx.ICON_INFORMATION))
        dlg.ShowModal()
        dlg.Destroy()
        


    def stopBackgroundGraphing(self):
        # print 'stop graphing me'
        noop = 1

    #####################
    # 
    # drawing live graphs
    # 
    #  as with history, two options for getting data - directly from a COM port,
    #   or remotely via MQTT
    # 
    #  the functions will create a new tab to display the graph, and kick off a 
    #   new thread to keep it up to date

    def displayLiveConnectFailure(self, message):
        self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
        self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
        errdlg = wx.MessageDialog(self,
                                  message,
                                  'CurrentCost - live tab',
                                  style=(wx.OK | wx.ICON_EXCLAMATION))
        result = errdlg.ShowModal()
        errdlg.Destroy()

        
    # connecting directly 
    def onLiveConnectSerial (self, event):
        global livedataagent, plotter, ccdb, myserialconn

        if self.liveaxes == None:
            self.liveaxes = plotter.add('live').gca()
            plotter.selectpage('live')

        if livedataagent.connectionType == livedataagent.CONNECTION_SERIAL:
            # disconnect
            livedataagent.disconnect()
            # update the GUI to show what the user has selected
            self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
            self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
            return

        if livedataagent.connectionType == livedataagent.CONNECTION_MQTT:
            # disconnect any existing connection
            livedataagent.disconnect()


        # if already connected, we do not need to connect now
        reuseconnection = myserialconn.isConnected()

        if reuseconnection == True:
            # create a live data connection
            livedataagent.connect(self, livedataagent.CONNECTION_SERIAL, ccdb,
                                  self.liveaxes, 
                                  None, None, 
                                  myserialconn)
            
            # update the GUI to show what the user has selected
            self.MENU_LIVE.Check(self.MENU_LIVE_COM,  True)
            self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
        else:
            # serial port not already connected, so we need to connect now
            #
            # get information from the user required to establish the connection
            #  prefill with setting from database if possible
            #
            dlg = wx.TextEntryDialog(self, 'Specify the COM port to connect to:','CurrentCost')
            lastcom = ccdb.RetrieveSetting("comport")
            if lastcom:
                dlg.SetValue(lastcom)
            if dlg.ShowModal() == wx.ID_OK:
                newcom = dlg.GetValue()
                if lastcom != newcom:
                    ccdb.StoreSetting("comport", newcom)
    
                try:
                    # connect to the CurrentCost meter
                    #
                    # we *hope* that the serialconn class will automatically handle what
                    # connection settings (other than COM port number) are required for the
                    # model of CurrentCost meter we are using
                    #
                    # the serialconn class does not handle serial exceptions - we need to
                    # catch and handle these ourselves
                    # (the only exception to this is that it will close the connection
                    #  in the event of an error, so we do not need to do this explicitly)
                    myserialconn.connect(newcom)
                except serial.SerialException, msg:
                    errdlg = wx.MessageDialog(None,
                                              'Serial Exception: ' + str(msg),
                                              'Failed to connect to CurrentCost meter',
                                              style=(wx.OK | wx.ICON_EXCLAMATION))
                    errdlg.ShowModal()
                    errdlg.Destroy()
                    self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                    self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
                    return False
                except:
                    errdlg = wx.MessageDialog(None,
                                              'CurrentCost',
                                              'Failed to connect to CurrentCost meter',
                                              style=(wx.OK | wx.ICON_EXCLAMATION))
                    errdlg.ShowModal()
                    errdlg.Destroy()
                    self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                    self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
                    return False
    
                # create a new connection
                livedataagent.connect(self, livedataagent.CONNECTION_SERIAL, ccdb,
                                      self.liveaxes, 
                                      None, None, 
                                      myserialconn)
                
                # update the GUI to show what the user has selected
                self.MENU_LIVE.Check(self.MENU_LIVE_COM,  True)
                self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
            else:
                # update the GUI to show that the user has cancelled
                self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)                
            dlg.Destroy()



    # connecting via MQTT
    def onLiveConnectMQTT (self, event):
        global livedataagent, plotter, ccdb

        if self.IsMQTTSupportAvailable():
            if self.liveaxes == None:
                self.liveaxes = plotter.add('live').gca()
                plotter.selectpage('live')

            if livedataagent.connectionType == livedataagent.CONNECTION_MQTT:
                # disconnect
                livedataagent.disconnect()
                # update the GUI to show what the user has selected
                self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
                return

            if livedataagent.connectionType == livedataagent.CONNECTION_SERIAL:
                # disconnect any existing connection
                livedataagent.disconnect()

            #
            # get information from the user required to establish the connection
            #  prefill with setting from database if possible
            #
    
            # IP address
    
            dlg = wx.TextEntryDialog(self, 
                                     'Specify the IP address or hostname of a message broker to connect to:',
                                     'CurrentCost')
            lastipaddr = ccdb.RetrieveSetting("mqttipaddress")
            if lastipaddr:
                dlg.SetValue(lastipaddr)
            else:
                dlg.SetValue('204.146.213.96')
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
                return False
            ipaddr = dlg.GetValue()
            if lastipaddr != ipaddr:
                ccdb.StoreSetting("mqttipaddress", ipaddr)
            dlg.Destroy()
    
            # topic string
    
            dlg = wx.TextEntryDialog(self, 
                                     'Specify the topic string to subscribe to:',
                                     'CurrentCost')
            lasttopicstring = ccdb.RetrieveSetting("mqttlivetopicstring")
            if lasttopicstring:
                dlg.SetValue(lasttopicstring)
            else:
                dlg.SetValue('PowerMeter/CC/YourUserNameHere')
            if dlg.ShowModal() != wx.ID_OK:
                dlg.Destroy()
                self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
                self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)
                return False
            topicString = dlg.GetValue()
            if lasttopicstring != topicString:
                ccdb.StoreSetting("mqttlivetopicstring", topicString)
            dlg.Destroy()

            # create a new connection
            livedataagent.connect(self, livedataagent.CONNECTION_MQTT, ccdb,
                                  self.liveaxes, 
                                  ipaddr, topicString, 
                                  None)                
            
            # update the GUI to show what the user has selected
            self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
            self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, True)            
        else:
            dlg = wx.MessageDialog(self,
                                   "Connecting via MQTT requires the use of a third-party module. "
                                   "This module is not present.\n\n"
                                   "Please copy the MQTT library to the directory where the CurrentCost app is stored then try this again",
                                   'CurrentCost', 
                                   style=(wx.OK | wx.ICON_EXCLAMATION))
            dlg.ShowModal()        
            dlg.Destroy()

            # update the GUI to show what the user has selected
            self.MENU_LIVE.Check(self.MENU_LIVE_COM,  False)
            self.MENU_LIVE.Check(self.MENU_LIVE_MQTT, False)  

        return


    #########################################
    # 
    # National Grid data
    # 
    #  show National Grid realtime data on the live graph
    # 

    def onNationalGridDemand(self, event):
        global livedataagent, plotter, ccdb 

        if self.liveaxes == None:
            self.liveaxes = plotter.add('live').gca()
            plotter.selectpage('live')

        # we cannot show demand and frequency at the same time, so we toggle
        # between them here - switching off the frequency graphing if it was on
        if livedataagent.showNationalGridFrequency == True:
            # disable frequency graphing
            livedataagent.pauseNationalGridFrequencyData()
            # the National Grid data is shown on a secondary axes (created by
            #  twinx). annoyingly, we can't remove secondary axes. 
            # so we're stuck with having to delete the whole page, and recreate
            #  the CurrentCost data graph we want to keep
            # this means any existing handles to the graph axes (self.liveaxes)
            #  will be invalid, so we have to inform every possible object 
            #  which has cached the handle. damn.
            plotter.deletepage('live')
            self.liveaxes = plotter.add('live').gca()
            plotter.selectpage('live')
            livedataagent.prepareCurrentcostDataGraph(self.liveaxes)
            # update the interface to show the selected graph type
            self.MENU_LIVE.Check(self.MENU_LIVE_SUPPLY, False)

        if livedataagent.showNationalGridDemand == True:
            livedataagent.stopNationalGridDemandData()
        else:
            livedataagent.startNationalGridDemandData(self.liveaxes)


    def onNationalGridFreq(self, event):
        global livedataagent, plotter, ccdb 

        if self.liveaxes == None:
            self.liveaxes = plotter.add('live').gca()
            plotter.selectpage('live')

        # we cannot show demand and frequency at the same time, so we toggle
        # between them here - switching off the demand graphing if it was on
        if livedataagent.showNationalGridDemand == True:
            # disable demand graphing
            livedataagent.pauseNationalGridDemandData()
            # the National Grid data is shown on a secondary axes (created by
            #  twinx). annoyingly, we can't remove secondary axes. 
            # so we're stuck with having to delete the whole page, and recreate
            #  the CurrentCost data graph we want to keep
            # this means any existing handles to the graph axes (self.liveaxes)
            #  will be invalid, so we have to inform every possible object 
            #  which has cached the handle. damn.
            plotter.deletepage('live')
            self.liveaxes = plotter.add('live').gca()
            plotter.selectpage('live')
            livedataagent.prepareCurrentcostDataGraph(self.liveaxes)
            # update the interface to show the selected graph type
            self.MENU_LIVE.Check(self.MENU_LIVE_DEMAND, False)

        if livedataagent.showNationalGridFrequency == True:
            livedataagent.stopNationalGridFrequencyData()
        else:
            livedataagent.startNationalGridFrequencyData(self.liveaxes)


    def onNationalGridGen(self, event):
        global trc, livedataagent, plotter
        trc.FunctionEntry("onNationalGridGen")

        if self.liveaxes == None:
            trc.Trace("no live data to display")
            dlg = wx.MessageDialog(self,
                                   "This function displays data from the 'live' tab, breaking it down into the "
                                   "different sources of the generated electricity\n\n"
                                   "Please start the live graphing first before using this.",
                                   'CurrentCost', 
                                   style=(wx.OK | wx.ICON_EXCLAMATION))
            dlg.ShowModal()        
            dlg.Destroy()
            trc.FunctionExit("onNationalGridGen")
            return

        trc.Trace("creating a new tab to display the generation data")
        plotter.deletepage('source')
        newSourceTab = plotter.add('source').gca()
        plotter.selectpage('source')

        trc.Trace("displaying the stacked graph")
        livedataagent.prepareElectricitySourceGraph(newSourceTab)

        trc.FunctionExit("onNationalGridGen")


    #
    # prompt the user for a 'cost per kwh' value
    # 
    #  if promptEvenIfStored is false, we return the value stored in settings db
    #   immediately if we have it.
    # 
    #  if promptEvenIfStored is true, or we have no value stored, then we prompt
    #   the user to give a value
    # 
    def getKWHCost(self, promptEvenIfStored):
        # retrieve the last-used setting
        lastkwh = ccdb.RetrieveSetting("kwhcost")

        if lastkwh and promptEvenIfStored == False:
            return lastkwh

        newkwh = None

        dlg = wx.TextEntryDialog(self, 'Cost of electricity (in � per kWh):','CurrentCost')
        if lastkwh:
            dlg.SetValue(lastkwh)
        if dlg.ShowModal() == wx.ID_OK:
            test = None
            while test == None:
                newkwh = dlg.GetValue()
                try:
                    # check that we have been given a value that can be turned
                    #  into a number
                    test = float(newkwh)
                except:
                    errdlg = wx.MessageDialog(None,
                                              'Not a number',
                                              'CurrentCost', 
                                              style=(wx.OK | wx.ICON_EXCLAMATION))
                    errdlg.ShowModal()        
                    errdlg.Destroy()
                    newkwh = dlg.ShowModal()
                  
            newkwh = test
            ccdb.StoreSetting("kwhcost", newkwh)

        dlg.Destroy()
        return newkwh



    #
    # prompt the user for a 'electricity supplier' value
    #  given the name of an electricity supplier, returns the kg of CO2 per kwh
    # 
    #  if promptEvenIfStored is false, we return the value stored in settings db
    #   immediately if we have it.
    # 
    #  if promptEvenIfStored is true, or we have no value stored, then we prompt
    #   the user to give a value
    # 
    def getKgCO2PerKWh(self, promptEvenIfStored):
        global CO2_BY_SUPPLIERS, kgCO2PerKWh

        # retrieve cached value
        if kgCO2PerKWh and promptEvenIfStored == False:
            return kgCO2PerKWh

        # retrieve the last-used setting
        suppliername = ccdb.RetrieveSetting("electricitysupplier")
        if suppliername and promptEvenIfStored == False:
            if suppliername not in CO2_BY_SUPPLIERS.keys():
                suppliername = 'Any other UK supplier'
                ccdb.StoreSetting("electricitysupplier", suppliername)
            kgCO2PerKWh = CO2_BY_SUPPLIERS[suppliername]
            return kgCO2PerKWh

        # get a new setting from the user
        newsupplier = None
        dlg = wx.SingleChoiceDialog(self, 
                                    'Who is your electricity supplier?',
                                    'CurrentCost',
                                    CO2_BY_SUPPLIERS.keys(),
                                    style=(wx.OK | wx.DEFAULT_DIALOG_STYLE))
        dlg.ShowModal()
        newsupplier = dlg.GetStringSelection()
        if newsupplier not in CO2_BY_SUPPLIERS.keys():
            newsupplier = 'Any other UK supplier'
        ccdb.StoreSetting("electricitysupplier", newsupplier)        
        dlg.Destroy()

        # return CO2 value
        kgCO2PerKWh = CO2_BY_SUPPLIERS[newsupplier]
        return kgCO2PerKWh


    #
    # set a target for electricity usage
    # 
    def onSetUsageTarget(self, event):
        global ccdb

        # retrieve existing preference for whether targets should be shown
        #  and invert
        enableTarget = ccdb.RetrieveSetting("enabletarget")
        if enableTarget == '0':
            # currently false - set to True
            successful = self.enableUsageTarget()
            if successful == True:
                enableTarget = True
                ccdb.StoreSetting("enabletarget", 1) 
            else:
                enableTarget = False
        else:
            # currently true - set to False
            enableTarget = False
            ccdb.StoreSetting("enabletarget", 0)
            self.disableUsageTarget()
        
        self.f1.Check(self.MENU_TARGET, enableTarget)

    def disableUsageTarget(self):
        global targetlines, ccvis

        try:
            ccvis.DeleteTargetLine(targetlines[self.axes1], self.axes1)
        except:
            # noop
            i = 0
        try:
            ccvis.DeleteTargetLine(targetlines[self.axes2], self.axes2)
        except:
            # noop
            i = 0
        try:
            ccvis.DeleteTargetLine(targetlines[self.axes3], self.axes3)
        except:
            # noop
            i = 0
        try:
            ccvis.DeleteTargetLine(targetlines[self.axes4], self.axes4)
        except:
            # noop
            i = 0
        try:
            ccvis.DeleteTargetLine(targetlines[self.axes5], self.axes5)
        except:
            # noop
            i = 0

    def enableUsageTarget(self):
        dlg = wx.TextEntryDialog(self, 'How much do you want to spend a year on electricity? (�)','CurrentCost')
        # retrieve the last-used setting
        annualtarget = ccdb.RetrieveSetting("annualtarget")
        if annualtarget:
            dlg.SetValue(annualtarget)
        if dlg.ShowModal() == wx.ID_OK:
            newannualtarget = dlg.GetValue()
            annualtargetfloat = None
            try:
                # check that we have been given a value that can be turned
                #  into a number
                annualtargetfloat = float(newannualtarget)
            except:
                errdlg = wx.MessageDialog(None,
                                          'Not a number',
                                          'CurrentCost', 
                                          style=(wx.OK | wx.ICON_EXCLAMATION))
                errdlg.ShowModal()        
                errdlg.Destroy()
                dlg.Destroy()
                return False

            if annualtargetfloat != None:
                if annualtarget != newannualtarget:
                    ccdb.StoreSetting("annualtarget", annualtargetfloat)

                # we now have a total spend. do we know how much a kwh costs?
                kwhcost = self.getKWHCost(False)

                if kwhcost:
                    self.displayUsageTarget()
                    dlg.Destroy()
                    return True
                        
        dlg.Destroy()
        return False


    def displayUsageTarget(self):
        global ccdb, ccvis, targetlines
    
        annualtarget = ccdb.RetrieveSetting("annualtarget")
        annualtargetfloat = float(annualtarget)
        kwhcost = self.getKWHCost(False)

        # what unit are we using to plot?
        #  we internally store everything in kWh, so if we want to display it in 
        #   another unit, we need to know what to multiply the kWh by to get the 
        #   value for displaying
        kwhfactor = 1
        graphUnit = ccdb.RetrieveSetting("graphunits")
        if graphUnit == ccvis.GRAPHUNIT_KEY_GBP:
            kwhfactor = float(kwhcost)
        elif graphUnit == ccvis.GRAPHUNIT_KEY_CO2:
            kwhfactor = float(self.getKgCO2PerKWh(False))

        # recap:
        # annualtargetfloat - � to spend in a year
        # kwhcost           - � per kwh
        # 
        annualkwh  = annualtargetfloat / float(kwhcost)
        monthlykwh = annualkwh / 12
        dailykwh   = annualkwh / 365
        hourlykwh  = annualkwh / 4380

        try:
            targetlines[self.axes1] = ccvis.DrawTargetLine(hourlykwh, self.axes1, kwhfactor)
        except:
            # noop
            i = 0
        try:
            targetlines[self.axes2] = ccvis.DrawTargetLine(dailykwh, self.axes2, kwhfactor)
        except:
            # noop
            i = 0
        try:
            targetlines[self.axes3] = ccvis.DrawTargetLine(monthlykwh, self.axes3, kwhfactor)
        except:
            # noop
            i = 0    
        try:
            targetlines[self.axes4] = ccvis.DrawTargetLine(hourlykwh, self.axes4, kwhfactor)
        except:
            # noop
            i = 0    
        try:
            targetlines[self.axes5] = ccvis.DrawTargetLine(dailykwh, self.axes5, kwhfactor)
        except:
            # noop
            i = 0    

    #
    # redraw the graphs to use kWh as a unit in the graph
    #
    def onShowKWH (self, event):
        global ccdb, ccvis

        # update the GUI to show what the user has selected
        self.f1.Check(self.MENU_SHOWKWH, True)
        self.f1.Check(self.MENU_SHOWGBP, False)
        self.f1.Check(self.MENU_SHOWCO2, False)

        # store the setting
        ccvis.graphunitslabel = ccvis.GRAPHUNIT_LABEL_KWH
        ccdb.StoreSetting("graphunits", ccvis.GRAPHUNIT_KEY_KWH)

        # redraw the graphs
        progdlg = wx.ProgressDialog ('CurrentCost', 
                                     'Initialising CurrentCost data store', 
                                     maximum = 11, 
                                     style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
        drawMyGraphs(self, progdlg, True)
        progdlg.Destroy()

    #
    # redraw the graphs to use financial cost as the units in the graph
    # 
    def onShowGBP (self, event):
        global ccdb, ccvis
        #
        if self.getKWHCost(True):
            # store the setting
            ccvis.graphunitslabel = ccvis.GRAPHUNIT_LABEL_GBP
            ccdb.StoreSetting("graphunits", ccvis.GRAPHUNIT_KEY_GBP)  
            # update the GUI
            self.f1.Check(self.MENU_SHOWKWH, False)
            self.f1.Check(self.MENU_SHOWGBP, True)
            self.f1.Check(self.MENU_SHOWCO2, False)
            # redraw the graphs
            progdlg = wx.ProgressDialog ('CurrentCost', 
                                         'Initialising CurrentCost data store', 
                                         maximum = 11, 
                                         style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
            drawMyGraphs(self, progdlg, True)
            progdlg.Destroy()
        else:
            self.f1.Check(self.MENU_SHOWKWH, True)
            self.f1.Check(self.MENU_SHOWGBP, False)
            self.f1.Check(self.MENU_SHOWCO2, False)

    #
    # redraw the graphs to use CO2 as a unit in the graph
    #
    def onShowCO2 (self, event):
        global ccdb, ccvis

        # update the GUI to show what the user has selected
        self.f1.Check(self.MENU_SHOWKWH, False)
        self.f1.Check(self.MENU_SHOWGBP, False)
        self.f1.Check(self.MENU_SHOWCO2, True)

        # store the setting
        ccvis.graphunitslabel = ccvis.GRAPHUNIT_LABEL_CO2
        ccdb.StoreSetting("graphunits", ccvis.GRAPHUNIT_KEY_CO2)

        # force user to re-select electricity supplier
        self.getKgCO2PerKWh(True)

        # redraw the graphs
        progdlg = wx.ProgressDialog ('CurrentCost', 
                                     'Initialising CurrentCost data store', 
                                     maximum = 11, 
                                     style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
        drawMyGraphs(self, progdlg, True)
        progdlg.Destroy()


#
# GLOBAL FUNCTIONS
# 

def getDataFromCurrentCostMeter(portdet, dialog):
    global ccdb, myparser, myserialconn, trc
    trc.FunctionEntry("getDataFromCurrentCostMeter")
    # 
    dialog.Update(0, 'Connecting to local CurrentCost meter - using device "' + portdet + '"')

    # if already connected, we:
    #  a) do not need to connect now
    #  b) should not disconnect once complete
    reuseconnection = myserialconn.isConnected()

    if reuseconnection == False:
        try:
            # connect to the CurrentCost meter
            #
            # we *hope* that the serialconn class will automatically handle what 
            # connection settings (other than COM port number) are required for the
            # model of CurrentCost meter we are using 
            # 
            # the serialconn class does not handle serial exceptions - we need to 
            # catch and handle these ourselves
            # (the only exception to this is that it will close the connection 
            #  in the event of an error, so we do not need to do this explicitly)
            myserialconn.connect(portdet)
        except serial.SerialException, msg:
            trc.Error("Failed to receive data from CurrentCost meter")
            trc.Error("SerialException: " + str(msg))

            dialog.Update(11, 'Failed to connect to CurrentCost meter')
            errdlg = wx.MessageDialog(None,
                                      'Serial Exception: ' + str(msg),
                                      'Failed to connect to CurrentCost meter', 
                                      style=(wx.OK | wx.ICON_EXCLAMATION))
            errdlg.ShowModal()        
            errdlg.Destroy()
            trc.FunctionExit("getDataFromCurrentCostMeter")
            return False
        except:
            dialog.Update(11, 'Failed to connect to CurrentCost meter')
            trc.Error("Failed to connect to CurrentCost meter - unknown cause")
            trc.FunctionExit("getDataFromCurrentCostMeter")
            return False

    # we keep trying to get an update from the CurrentCost meter
    #  until we successfully populate the CurrentCost data object
    currentcoststruct = None

    # the newer CC128 meter splits the history data over multiple updates
    # we use this number to indicate how many updates are remaining
    updatesremaining = 1

    validLiveUpdates    = 0
    validHistoryUpdates = 0
    invalidUpdates      = 0

    loopMessage = "Waiting for data from CurrentCost meter"

    while updatesremaining > 0:
        (tocontinue, toskip) = dialog.Update(1, loopMessage)
        if tocontinue == False:
            if reuseconnection == False:
                loopMessage = "User cancelled. Closing connection to CurrentCost meter"
                trc.Trace(loopMessage)
                dialog.Update(10, loopMessage)
                myserialconn.disconnect()
            dialog.Update(11, 'Cancelled.')
            trc.FunctionExit("getDataFromCurrentCostMeter")
            return False

        # line of data received from serial port
        line = ""

        while len(line) == 0:
            try:
                line = myserialconn.readUpdate()
            except serial.SerialException, err:
                trc.Error("Failed to receive data from CurrentCost meter")
                trc.Error("SerialException: " + str(msg))
                dialog.Update(11, 'Failed to receive data from CurrentCost meter')
                errdlg = wx.MessageDialog(None,
                                          'Serial Exception: ' + str(err),
                                          'Failed to receive data from CurrentCost meter', 
                                          style=(wx.OK | wx.ICON_EXCLAMATION))
                errdlg.ShowModal()        
                errdlg.Destroy()
                trc.FunctionExit("getDataFromCurrentCostMeter")
                return False
            except Exception, msg:
                trc.Error("Failed to receive data from CurrentCost meter")
                trc.Error("Exception: " + str(msg))
                dialog.Update(11, 'Failed to receive data from CurrentCost meter')
                errdlg = wx.MessageDialog(None,
                                          'Exception: ' + str(msg),
                                          'Failed to receive data from CurrentCost meter', 
                                          style=(wx.OK | wx.ICON_EXCLAMATION))
                errdlg.ShowModal()        
                errdlg.Destroy()
                trc.FunctionExit("getDataFromCurrentCostMeter")
                return False

        trc.Trace("received line of XML from CurrentCost meter. about to parse")

        # try to parse the XML
        currentcoststruct = myparser.parseCurrentCostXML(line)

        if currentcoststruct == None:
            # something wrong with the line of xml we received
            invalidUpdates += 1
            loopMessage = datetime.datetime.now().strftime("%H:%M:%S") + \
                          " : Received " + \
                          str(validHistoryUpdates) + " updates with history data, " + \
                          str(validLiveUpdates) + " updates with live (no history) data \n" + \
                          str(invalidUpdates) + " invalid updates"
            dialog.Update(1, loopMessage)
            trc.Trace("Received data that could not be parsed")
        elif 'hist' not in currentcoststruct['msg']:
            # we received something which looked like valid CurrentCost data,
            #  but did not contain any history data
            # this means, either:
            #  a) something wrong - we need to wait for history data
            #  b) (CC128-only) the meter has finished outputting it's series of
            #        history updates, and has gone back to outputting live data
            #        in which case we have finished and need to break out of 
            #        the loop we are in
            trc.Trace("received (valid?) CurrentCost data without any history data")
            validLiveUpdates += 1

            loopMessage = datetime.datetime.now().strftime("%H:%M:%S") +  \
                          " : Received " + \
                          str(validHistoryUpdates) + " updates with history data, " + \
                          str(validLiveUpdates) + " updates with live (no history) data \n" + \
                          str(invalidUpdates) + " invalid updates"
            #loopMessage = datetime.datetime.now().strftime("%H:%M:%S") + " : Received data from CurrentCost meter (live only, no history information)"

            if type(currentcoststruct['msg']['src']) is unicode and currentcoststruct['msg']['src'].startswith('CC128-v0.'):
                # HACK!
                # this may or may not be true - there is a potential that a 
                # CC128 meter returned us some data (e.g. broken or partial XML)
                # that didn't contain <HIST> before we received a complete set
                # of history data
                # however, as the last update from the meter is not fixed (it can
                # be <h004> or <d001> or <m001>) it's hard to know what to look 
                # for as a reliable end point
                # for now, we just assume that when the meter stops outputting 
                # history, then it has finished correctly
                # probably something to come back to at a future date!
                trc.Trace("live data received from CC128. assuming that there is no history data remaining")
                if validHistoryUpdates > 0:
                    updatesremaining = 0
                dialog.Update(1, loopMessage)
            else:
                dialog.Update(1, loopMessage) # 'Waiting for history data from CurrentCost meter')
                trc.Trace("waiting for history data")
        else:
            # we have received history data - parse and store the CurrentCost 
            #  data in the datastore
            # the parser will return the number of updates still expected 
            #  (0 if this was the last or only expected update)
            updatesremaining = myparser.storeTimedCurrentCostData(ccdb)
            trc.Trace("stored history data. think there are now " + str(updatesremaining) + " updates remaining")
            validHistoryUpdates += 1
            loopMessage = datetime.datetime.now().strftime("%H:%M:%S") + \
                          " : Received " + \
                          str(validHistoryUpdates) + " updates with history data, " + \
                          str(validLiveUpdates) + " updates with live (no history) data \n" + \
                          str(invalidUpdates) + " invalid updates"

    dialog.Update(2, 'Received complete history data from CurrentCost meter')
    #
    if reuseconnection == False:
        myserialconn.disconnect()    
    #
    trc.FunctionExit("getDataFromCurrentCostMeter")
    return True


#
# redraw graphs on each of the tabs
# 
def drawMyGraphs(guihandle, dialog, changeaxesonly):
    global ccdb, ccvis, trc
    trc.FunctionEntry("drawMyGraphs")

    # what unit are we using to plot?
    #  we internally store everything in kWh, so if we want to display it in 
    #   another unit, we need to know what to multiply the kWh by to get the 
    #   value for displaying
    kwhfactor = 1
    graphUnit = ccdb.RetrieveSetting("graphunits")
    if graphUnit == ccvis.GRAPHUNIT_KEY_GBP:
        kwhfactor = float(ccdb.RetrieveSetting("kwhcost"))
    elif graphUnit == ccvis.GRAPHUNIT_KEY_CO2:
        kwhfactor = float(guihandle.getKgCO2PerKWh(False))

    hourDataCollection = ccdb.GetHourDataCollection()
    dayDataCollection = ccdb.GetDayDataCollection()
    monthDataCollection = ccdb.GetMonthDataCollection()

    if len(hourDataCollection) == 0:
        trc.Trace("Empty hour data collection")
        if dialog != None:
            dialog.Update(11, 'Data store initialised')
        trc.FunctionExit("drawMyGraphs")
        return

    if dialog != None:
        dialog.Update(3, 'Charting hourly electricity usage...')
        trc.Trace("charting hourly electricity usage")
    ccvis.PlotHourlyData(guihandle.axes1, hourDataCollection, kwhfactor)
    for storednote in ccdb.RetrieveAnnotations(1):
        ccvis.AddNote(storednote[0], # storednote[4], 
                      guihandle.axes1, 
                      storednote[1], 
                      storednote[2], 
                      storednote[5], 
                      kwhfactor,
                      "hours")        

    if dialog != None:
        dialog.Update(4, 'Charting daily electricity usage...')
        trc.Trace("charting daily electricity usage")
    ccvis.PlotDailyData(guihandle.axes2, dayDataCollection, kwhfactor)
    for storednote in ccdb.RetrieveAnnotations(2):
        ccvis.AddNote(storednote[0], # storednote[4], 
                      guihandle.axes2, 
                      storednote[1], 
                      storednote[2], 
                      storednote[5], 
                      kwhfactor,
                      "days")        

    if dialog != None:
        dialog.Update(5, 'Charting monthly electricity usage...')
        trc.Trace("charting monthly electricity usage")
    ccvis.PlotMonthlyData(guihandle.axes3, monthDataCollection, kwhfactor)
    for storednote in ccdb.RetrieveAnnotations(3):        
        ccvis.AddNote(storednote[0], # storednote[4], 
                      guihandle.axes3, 
                      storednote[1], 
                      storednote[2], 
                      storednote[5], 
                      kwhfactor,
                      "months")        

    ccdata = CurrentCostDataFunctions()
    averageDayData = ccdata.CalculateAverageDay(hourDataCollection)
    averageWeekData = ccdata.CalculateAverageWeek(dayDataCollection)

    if changeaxesonly == False:
        if dialog != None:
            dialog.Update(6, 'Identifying electricity usage trends...')
            trc.Trace("identifying usage trends")
        ccvis.IdentifyTrends(guihandle.trendspg, hourDataCollection, dayDataCollection, monthDataCollection)

    if dialog != None:
        dialog.Update(7, 'Charting an average day...')
        trc.Trace("charting average day")
    if averageDayData:
        ccvis.PlotAverageDay(averageDayData, guihandle.axes4, guihandle.trendspg, kwhfactor)

    if dialog != None:    
        dialog.Update(8, 'Charting an average week...')
        trc.Trace("charting average week")
    if averageWeekData:
        ccvis.PlotAverageWeek(averageWeekData, guihandle.axes5, guihandle.trendspg, kwhfactor)

    if dialog != None:
        dialog.Update(9, 'Formatting charts...')
    #    
    daysl = DayLocator() 
    hoursl = HourLocator(range(12,24,12)) 
    datesFmt = DateFormatter('%d %b')
    timesFmt = DateFormatter('%I%p') #('%H:%M')
    guihandle.axes1.xaxis.set_minor_formatter(timesFmt)
    guihandle.axes1.xaxis.set_major_formatter(datesFmt)
    guihandle.axes1.xaxis.set_major_locator(daysl) 
    guihandle.axes1.xaxis.set_minor_locator(hoursl)    
    # 
    # 
    daysFmt  = DateFormatter('%d')
    mthsFmt  = DateFormatter('%b %y')
    datesl = DayLocator(range(2,31,2)) 
    monthsl = MonthLocator()
    guihandle.axes2.xaxis.set_major_formatter(mthsFmt)
    guihandle.axes2.xaxis.set_major_locator(monthsl)
    guihandle.axes2.xaxis.set_minor_formatter(daysFmt)
    guihandle.axes2.xaxis.set_minor_locator(datesl)
    #
    monthsFmt = DateFormatter('%b')
    yearsFmt = DateFormatter('%Y')
    guihandle.axes3.xaxis.set_minor_formatter(monthsFmt)
    monthsl = MonthLocator(range(2,13,1))
    yearsl = YearLocator()
    guihandle.axes3.xaxis.set_major_locator(yearsl)
    guihandle.axes3.xaxis.set_minor_locator(monthsl)
    guihandle.axes3.xaxis.set_major_formatter(yearsFmt)
    #
    guihandle.axes4.xaxis.set_major_locator(HourLocator(range(1, 24, 2)))
    guihandle.axes4.xaxis.set_major_formatter(DateFormatter('%H00'))
    #
    guihandle.axes5.xaxis.set_major_locator(DayLocator(range(0,8,1)))
    guihandle.axes5.xaxis.set_major_formatter(DateFormatter('%a'))
    #
    if dialog != None:
        dialog.Update(10, 'Complete. Redrawing...')
    #
    try:
        guihandle.axes1.figure.canvas.draw()
    except:
        trc.Trace("failed to draw canvas on hourly page")
        plotter.deletepage('hourly')
    try:
        guihandle.axes2.figure.canvas.draw()
    except:
        trc.Trace("failed to draw canvas on daily page")
        plotter.deletepage('daily')
    try:
        guihandle.axes3.figure.canvas.draw() # error?
    except:
        trc.Trace("failed to draw canvas on monthly page")
        plotter.deletepage('monthly')
    try:
        guihandle.axes4.figure.canvas.draw()
    except:
        trc.Trace("failed to draw canvas on average day page")
        plotter.deletepage('average day')
    try:
        guihandle.axes5.figure.canvas.draw()
    except:
        trc.Trace("failed to draw canvas on average week page")
        plotter.deletepage('average week')
    #
    # retrieve preference for whether targets should be shown
    enableTarget = ccdb.RetrieveSetting("enabletarget")
    if enableTarget == '1':
        guihandle.displayUsageTarget()
    #
    if dialog != None:
        dialog.Update(11, 'Complete')

    trc.FunctionExit("drawMyGraphs")


#
# walks the user through connecting to the database used to persist 
#   historical CurrentCost usage data, and settings and preferences
# 
def connectToDatabase(guihandle):
    global ccdb, ccvis, trc
    trc.FunctionEntry("connectToDatabase")

    # what is the path to the database used to store CurrentCost data?
    dbLocation = ""

    # should the application prompt the user to select the database file?
    askForLocation = False
    # should the application store the location of the database file?
    storeLocation = False
    # is this the first time this application has been run?
    appFirstRun = False

    # message to be displayed when prompting for file location
    #  we tweak this message based on whether this is the first time the
    #  application is being run
    locMessage = "Identify file where CurrentCost data should be stored"

    # location of the executable. we store a small settings file, called
    #  currentcost.dat in this directory
    # this file will give the path of the database file where data is stored
    #  or 'prompt' if the user does not wants the path to be stored, and 
    #  wants to be prompted for the location every time
    currentdir = sys.path[0]

    # special case : py2exe-compiled apps store the zip in a different place
    if os.path.basename(currentdir) == "library.zip":
        currentdir = os.path.join(currentdir, "..")

    # location of the settings file
    settingsfile = os.path.join(currentdir, "currentcost.dat")

    # check if the settings file exists
    #  if not, then it is likely that this is the first time the application
    #  is run. we display an appropriate message, and set the flags to make 
    #  sure that some setup steps are run
    if os.path.isfile(settingsfile) == False:
        trc.Trace("Unable to find settings file")
        welcome = wx.MessageDialog(None,
                                   "It looks like this is the first time that you've used this application.\n\n"
                                   "The first thing that we need to do is to create a local file which the application can use to store historical CurrentCost readings. \n\n"
                                   "Once you click OK, the application will ask you to specify where you want this to be stored.\n\n"
                                   "After doing this, you can use 'Options'->'Connect' to get your first set of data from a connected CurrentCost meter",
                                   'Welcome to CurrentCost!', 
                                   style=(wx.OK | wx.ICON_INFORMATION))
        welcome.ShowModal()        
        welcome.Destroy()
        askForLocation = True
        appFirstRun = True
    else:        
        # the settings file does exist - we read it now
        trc.Trace("reading application settings file")
        settingscontents = open(settingsfile, 'r')
        dbLocation = settingscontents.read()
        settingscontents.close()

        # read the contents of the settings file - this will contain the path 
        #  of the database file where data is stored or 'prompt' if the user
        #  does not wants the path to be stored, and wants to be prompted for
        #  the location every time
        dbLocation = dbLocation.strip()
        if dbLocation == "prompt":
            # settings indicate 'prompt' - so we set flags to make sure that 
            #  the app prompts for the location of a database file
            trc.Trace("settings file set to 'prompt'")
            askForLocation = True
            locMessage = "Identify which CurrentCost data file you want to use"
        elif os.path.isfile(dbLocation) == False:
            # settings file gave a location of a database file, but no file
            #  could be found at that location. so we display an error, and set
            #  a flag so that a new location can be provided by the user
            trc.Error("unable to find database file at location identified in settings")
            trc.Error(" location : " + dbLocation)

            askForLocation = True
            storeLocation = True
            locMessage = "Identify the new location of the CurrentCost data file"
            errdlg = wx.MessageDialog(None,
                                      "The application failed to find the file used to store CurrentCost data.\n\n"
                                      "Please click 'OK', then help locate the file. \n\n"
                                      "If you no longer have this file, enter the location and name of a new file to create a new data store.",
                                      'Welcome to CurrentCost!', 
                                      style=(wx.OK | wx.ICON_EXCLAMATION))
            errdlg.ShowModal()        
            errdlg.Destroy()


    if askForLocation:
        trc.Trace("asking user for location of app database file")
        # for whatever reason, we need the user to provide the location of the 
        #  application's database file 
        dialog = wx.FileDialog(None, 
                               style = wx.OPEN, 
                               message=locMessage,
                               wildcard="CurrentCost data files (*.ccd)|*.ccd")

        if dialog.ShowModal() == wx.ID_OK:
            # new path provided
            #  we don't check it, as the user is allowed to create new files
            dbLocation = dialog.GetPath()
            trc.Trace("new location provided by user: " + dbLocation)
            dialog.Destroy()
        else:
            # user clicked 'cancel'
            #  there isn't much else we can do, so we display a 'goodbye' 
            #  message and quit
            dialog.Destroy()
            trc.Trace("user clicked cancel")
            byebye = wx.MessageDialog(None,
                                      "The application needs somewhere to store data. \n\n"
                                      "Sorry, without this, we need to end the app now. Hope you try again later!",
                                      'Welcome to CurrentCost!', 
                                      style=(wx.OK | wx.ICON_EXCLAMATION))
            byebye.ShowModal()        
            byebye.Destroy()
            trc.FunctionExit("connectToDatabase")
            return False


    # if this is the first time the application is being run, we provide two 
    #  options:
    #  1) store the new location, so that in future it is used on startup
    #  2) store 'prompt' as the new location, so the app will prompt for location
    #        every time

    if appFirstRun:
        dialog = wx.MessageDialog(None,
                                  "Do you want to use this file every time? \n\n"
                                  "If you click Yes, you will not be prompted for the location again \n"
                                  "If you click No, you will be prompted for the location every time the program starts",
                                  "Should this be your only CurrentCost file?",
                                  style=(wx.YES | wx.NO | wx.ICON_QUESTION))
        if dialog.ShowModal() == wx.ID_YES:
            trc.Trace("application to use this database file every time")
            storeLocation = True
        else:
            trc.Trace("application to prompt for database location on every run")
            settingscontents = open(settingsfile, 'w')
            settingscontents.write("prompt")
            settingscontents.close()
            
        dialog.Destroy()


    # we have all the information we need from the user
    #  time to run the startup process

    progdlg = wx.ProgressDialog ('CurrentCost', 
                                 'Initialising CurrentCost data store', 
                                 maximum = 11, 
                                 style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE)
    ccdb.InitialiseDB(dbLocation)

    if storeLocation:
        settingscontents = open(settingsfile, 'w')
        settingscontents.write(dbLocation)
        settingscontents.close()

    # retrieve preference for whether targets should be shown
    #  and cast to boolean    
    enableTarget = ccdb.RetrieveSetting("enabletarget")
    if enableTarget == None:
        enableTarget = 0
        ccdb.StoreSetting("enabletarget", enableTarget)
    if enableTarget == '0':
        enableTarget = False
    else:
        enableTarget = True
    guihandle.f1.Check(guihandle.MENU_TARGET, enableTarget)

    # retrieve preference for whether data should be shown in kWH, kg CO2 or �
    enableGraphUnit = ccdb.RetrieveSetting("graphunits")
    if enableGraphUnit != None:
        # we only need to do something if '�' or 'CO2' was persisted, otherwise
        #  just leave the default KWH setting
        if enableGraphUnit == ccvis.GRAPHUNIT_KEY_GBP:
            ccvis.graphunitslabel = ccvis.GRAPHUNIT_LABEL_GBP
            # update the GUI
            guihandle.f1.Check(guihandle.MENU_SHOWKWH, False)
            guihandle.f1.Check(guihandle.MENU_SHOWGBP, True)
            guihandle.f1.Check(guihandle.MENU_SHOWCO2, False)
        elif enableGraphUnit == ccvis.GRAPHUNIT_KEY_CO2:
            ccvis.graphunitslabel = ccvis.GRAPHUNIT_LABEL_CO2
            # update the GUI
            guihandle.f1.Check(guihandle.MENU_SHOWKWH, False)
            guihandle.f1.Check(guihandle.MENU_SHOWGBP, False)
            guihandle.f1.Check(guihandle.MENU_SHOWCO2, True)

    # draw the graphs

    drawMyGraphs(guihandle, progdlg, False)
    progdlg.Destroy()

    trc.FunctionExit("connectToDatabase")
    return True



#
# the user can add notes to the graph by clicking on bars
# 
# if the user click's on the note itself, the details of that note will be 
#  displayed. (unfinished)
def onMouseClick(event):
    global ccdb, frame, ccvis

    if isinstance(event.artist, Text):
        text = event.artist
        noteid = int(text.get_text())
        notetext = ccdb.RetrieveAnnotation(noteid)
        if notetext:
            if event.mouseevent.button == 1:
                displayNote = wx.MessageDialog(None, 
                                               notetext[4],
                                               'CurrentCost : Graph note',
                                               style=(wx.OK | wx.ICON_INFORMATION))
                displayNote.ShowModal()
            else:
                confdlg = wx.MessageDialog(None,
                                           'Do you want to delete the note: "' + notetext[4] + '"?',
                                           'CurrentCost', 
                                          style=(wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION))
                result = confdlg.ShowModal()        
                confdlg.Destroy()
                if result == wx.ID_YES:
                    ccdb.DeleteAnnotation(noteid)
                    confdlg = wx.MessageDialog(None, "Note will be removed when the app is restarted", "CurrentCost",
                                               style=(wx.OK | wx.ICON_INFORMATION))
                    confdlg.ShowModal()
                    confdlg.Destroy()
                
    elif isinstance(event.artist, Rectangle):
        clickedbar = event.artist
        atimestamp = clickedbar.get_x()
        clickedtimestamp = math.floor(atimestamp)
        fraction = atimestamp - clickedtimestamp
        clickeddatetime = datetime.datetime.fromordinal(int(clickedtimestamp))
        clickedkwh = None
        clickedgraph = None
        kwhcost = 1
    
        if ccvis.graphunitslabel == ccvis.GRAPHUNIT_LABEL_KWH:
            clickedkwh = clickedbar.get_height()
        elif ccvis.graphunitslabel == ccvis.GRAPHUNIT_LABEL_CO2:
            # request electricity supplier
            kgCO2PerKWh = frame.getKgCO2PerKWh(False)
            clickedkwh = clickedbar.get_height() / float(kgCO2PerKWh)
        else: # elif ccvis.graphunitslabel == ccvis.GRAPHUNIT_LABEL_GBP 
            kwhcost = frame.getKWHCost(False)
            clickedkwh = clickedbar.get_height() / float(kwhcost)
    
        clickedaxes = clickedbar.get_axes()
        if clickedaxes == frame.axes1:
            clickedgraph = "hours"        
        elif clickedaxes == frame.axes2:
            clickedgraph = "days"
        elif clickedaxes == frame.axes3:
            clickedgraph = "months"
    
        dlg = wx.TextEntryDialog(None, 'Add a note:','CurrentCost')
        if dlg.ShowModal() == wx.ID_OK:
            newnote = dlg.GetValue()

            rowid = ccdb.StoreAnnotation(clickeddatetime, fraction, clickedgraph, newnote, clickedkwh)

            ccvis.AddNote(rowid, clickedaxes, clickeddatetime, fraction, clickedkwh, clickedkwh, clickedgraph)        
        dlg.Destroy()



def appInit():
    global frame, plotter, trc
    trc.FunctionEntry("appInit")

    app = wx.App()
    frame = MyFrame(None,-1,'CurrentCost')
    #
    plotter = PlotNotebook(frame)
    # 
    frame.trendspg = plotter.addtextpage('trends')
    frame.axes1    = plotter.add('hourly').gca()
    frame.axes2    = plotter.add('daily').gca()
    frame.axes3    = plotter.add('monthly').gca()    
    frame.axes4    = plotter.add('average day').gca()
    frame.axes5    = plotter.add('average week').gca()
    #
    frame.axes1.figure.canvas.mpl_connect('motion_notify_event', frame.UpdateStatusBar)    
    frame.axes2.figure.canvas.mpl_connect('motion_notify_event', frame.UpdateStatusBar)
    frame.axes3.figure.canvas.mpl_connect('motion_notify_event', frame.UpdateStatusBar)
    frame.axes4.figure.canvas.mpl_connect('motion_notify_event', frame.UpdateStatusBar)
    frame.axes5.figure.canvas.mpl_connect('motion_notify_event', frame.UpdateStatusBar)
    #
    frame.axes1.figure.canvas.mpl_connect('pick_event', onMouseClick)
    frame.axes2.figure.canvas.mpl_connect('pick_event', onMouseClick)
    frame.axes3.figure.canvas.mpl_connect('pick_event', onMouseClick)
    # 
    frame.Show()
    #
    if connectToDatabase(frame) == False:
        trc.FunctionExit("appInit")
        return
    app.MainLoop()
    trc.FunctionExit("appInit")

    


debug = False
options, rem = getopt.getopt(sys.argv[1:], '', ['debug'])
for opt, arg in options:
    if opt == '--debug':
        debug = True

trc.EnableTrace(debug)
trc.InitialiseTraceFile()


if __name__ == "__main__": 
    try:
        appInit()
    except Exception, exc:
        trc.Error("Unhandled exception")
        trc.Error(str(exc))

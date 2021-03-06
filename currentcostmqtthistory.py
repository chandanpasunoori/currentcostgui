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
import time
import string
from string import atoi, atof

from mqttClient import *
from currentcostdata import CurrentCostUpdate

#
# Many CurrentCost users have their meters connected to a RSMB (Really Small
#  Message Broker) which means they may not want to disconnect it from this to 
#  be able to use this app. 
#  
# So we provide the ability to receive CurrentCost data via MQTT. This also 
#  lets us use the program remotely.
# 
# This class is used to provide the MQTT connection to download historical data.
# 
# 
#  Dale Lane (http://dalelane.co.uk/blog)


class CurrentCostMQTTHistoryConnection():

    subscriber = None
    
    #
    # Establish a connection to the MQTT broker
    # 
    def EstablishConnection(self, ipaddr, topicString, guihandle):
        #
        # try and make the connection to the Broker
        # 

        connection = None
        try:
            connection = MqttConnection("currentcostguihistory", ipaddr)
            connection.connect()
        except ConnectFailedException, exception:
            guihandle.exitOnError("Unable to connect (" + str(exception) + ")")
            return

        #
        # define a subscription with the Broker
        # 

        subscriber = None
        topic = str(topicString) + '/+'
        try:
            self.subscriber = CurrentCostMQTTSubscriber(connection, topic)
            self.subscriber.registerGuiCallbacks(guihandle, connection)
            self.subscriber.subscribe()
        except SubscribeFailedException, exception:
            guihandle.exitOnError("Unable to subscribe to topic (" + str(exception) + ")")
            return

    #
    # Disconnect from the MQTT broker
    # 
    def Disconnect(self):
        if self.subscriber != None:
            self.subscriber.endconnection()
            
    

#
# Implements the actual MQTT subscriber
# 
class CurrentCostMQTTSubscriber(MqttSubscriber):

    # where to send the data received
    guicallback = None
    # a handle to the MQTT client to use when disconnecting
    mqttconnection = None

    # store handles to use for callbacks
    def registerGuiCallbacks(self, ccgui, connection):
        self.guicallback = ccgui
        self.mqttconnection = connection

    #
    # current version of the MQTT CurrentCost perl publishing script publishes
    #  history data as retained publications, republishing only when the data
    #  changes
    # this means after subscribing, we quickly get history data for hours, days
    #  and months, but then nothing for potentially a couple of hours until the
    #  hours history changes
    # as a result, we send back data to the GUI as soon as we get it - hourly 
    #  data will be received every couple of hours, daily data once a day, etc.
    # if we waited until we also got monthly data, we'd have a long wait!
    # 
    def messageReceived(self, message):
        MqttSubscriber.messageReceived(self, message)

        dataType = str(message.topicName[len(self.getTopic()) - 1:len(message.topicName)])

        msgdata = str(message.data)
        msgdataelems = string.split(msgdata)

        if dataType == "hours":
            ccUpdate = CurrentCostUpdate()
            ccUpdate.kWattsHour02 = atof(msgdataelems[0])
            ccUpdate.kWattsHour04 = atof(msgdataelems[1])
            ccUpdate.kWattsHour06 = atof(msgdataelems[2])
            ccUpdate.kWattsHour08 = atof(msgdataelems[3])
            ccUpdate.kWattsHour10 = atof(msgdataelems[4])
            ccUpdate.kWattsHour12 = atof(msgdataelems[5])
            ccUpdate.kWattsHour14 = atof(msgdataelems[6])
            ccUpdate.kWattsHour16 = atof(msgdataelems[7])
            ccUpdate.kWattsHour18 = atof(msgdataelems[8])
            ccUpdate.kWattsHour20 = atof(msgdataelems[9])
            ccUpdate.kWattsHour22 = atof(msgdataelems[10])
            ccUpdate.kWattsHour24 = atof(msgdataelems[11])
            ccUpdate.kWattsHour26 = atof(msgdataelems[12])
            self.guicallback.updateData(ccUpdate)
        elif dataType == "days":
            ccUpdate = CurrentCostUpdate()
            ccUpdate.WattsDay01 = atoi(msgdataelems[0])
            ccUpdate.WattsDay02 = atoi(msgdataelems[1])
            ccUpdate.WattsDay03 = atoi(msgdataelems[2])
            ccUpdate.WattsDay04 = atoi(msgdataelems[3])
            ccUpdate.WattsDay05 = atoi(msgdataelems[4])
            ccUpdate.WattsDay06 = atoi(msgdataelems[5])
            ccUpdate.WattsDay07 = atoi(msgdataelems[6])
            ccUpdate.WattsDay08 = atoi(msgdataelems[7])
            ccUpdate.WattsDay09 = atoi(msgdataelems[8])
            ccUpdate.WattsDay10 = atoi(msgdataelems[9])
            ccUpdate.WattsDay11 = atoi(msgdataelems[10])
            ccUpdate.WattsDay12 = atoi(msgdataelems[11])
            ccUpdate.WattsDay13 = atoi(msgdataelems[12])
            ccUpdate.WattsDay14 = atoi(msgdataelems[13])
            ccUpdate.WattsDay15 = atoi(msgdataelems[14])
            ccUpdate.WattsDay16 = atoi(msgdataelems[15])
            ccUpdate.WattsDay17 = atoi(msgdataelems[16])
            ccUpdate.WattsDay18 = atoi(msgdataelems[17])
            ccUpdate.WattsDay19 = atoi(msgdataelems[18])
            ccUpdate.WattsDay20 = atoi(msgdataelems[19])
            ccUpdate.WattsDay21 = atoi(msgdataelems[20])
            ccUpdate.WattsDay22 = atoi(msgdataelems[21])
            ccUpdate.WattsDay23 = atoi(msgdataelems[22])
            ccUpdate.WattsDay24 = atoi(msgdataelems[23])
            ccUpdate.WattsDay25 = atoi(msgdataelems[24])
            ccUpdate.WattsDay26 = atoi(msgdataelems[25])
            ccUpdate.WattsDay27 = atoi(msgdataelems[26])
            ccUpdate.WattsDay28 = atoi(msgdataelems[27])
            ccUpdate.WattsDay29 = atoi(msgdataelems[28])
            ccUpdate.WattsDay30 = atoi(msgdataelems[29])
            ccUpdate.WattsDay31 = atoi(msgdataelems[30])
            self.guicallback.updateData(ccUpdate)
        elif dataType == "months":
            ccUpdate = CurrentCostUpdate()
            ccUpdate.WattsMonth01 = atoi(msgdataelems[0])
            ccUpdate.WattsMonth02 = atoi(msgdataelems[1])
            ccUpdate.WattsMonth03 = atoi(msgdataelems[2])
            ccUpdate.WattsMonth04 = atoi(msgdataelems[3])
            ccUpdate.WattsMonth05 = atoi(msgdataelems[4])
            ccUpdate.WattsMonth06 = atoi(msgdataelems[5])
            ccUpdate.WattsMonth07 = atoi(msgdataelems[6])
            ccUpdate.WattsMonth08 = atoi(msgdataelems[7])
            ccUpdate.WattsMonth09 = atoi(msgdataelems[8])
            ccUpdate.WattsMonth10 = atoi(msgdataelems[9])
            ccUpdate.WattsMonth11 = atoi(msgdataelems[10])
            ccUpdate.WattsMonth12 = atoi(msgdataelems[11])
            self.guicallback.updateData(ccUpdate)



    # disconnect when complete
    def endconnection(self):
        try:
            self.unsubscribe()
        except UnsubscribeFailedException, exception:
            # print str(exception)
            noop = 1
        try:
            self.mqttconnection.disconnect()
        except DisconnectFailedException, exception:
            # print str(exception)
            noop = 1


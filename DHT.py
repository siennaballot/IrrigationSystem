#!/usr/bin/env python3
########################################################################
# Filename    : DHT.py
# Description : Use the DHT to get local humidity and temperature data
#               Use this data to calculate irrigation time
# Author      : Sienna Ballot
# modification: 6/3/19
########################################################################

import threading
import time
import RPi.GPIO as GPIO
import Freenove_DHT as DHT
import Relay
import csv
import CIMIS

thermoPin = 11
localHumidity = 0.0
localTemp = 0.0
hour = 0
irrigationTime = 0.0
sqft = 200          # 200 square feet to be irrigated
pf = 1.0            # plant factor for lawn
conversion = 0.62   # constant conversion factor
IE = 0.75           # irrigation efficiency (suggested to use 0.75)
systemRate = 17     # 17 gallons per minute = 1020 gallons per hour
ET0 = 0
cimisHumidity = 0
cimisTemp = 0
cimisET = 0

display = False

def getIrrigationTime():
    global irrigationTime
    global ET0
    global cimisET
    global cimisHumidity
    global cimisTemp

    # get ET, humidity, and temp from CIMIS
    #cimisHumidity = 76 #[76, 71, 65]
    #cimisTemp = 61.3 #[61.3, 63.8, 66.8]
    #cimisET = 0.01 #[0.01, 0.02, 0.03]

    # get humidty and temp derating factors 
    # get ET0 for the 3 hours using these factors and CIMIS ET
    # for i in range(0, 2):
    #     humidityDerate = localHumidity[i] / cimisHumidity[i]
    #     tempDerate = localTemp[i] / cimisTemp[i]
    #     ET0 = ET0 + (cimisET[i] / (tempDerate * humidityDerate))
    
    result = time.localtime(time.time())
    CIMIS.getcimisdata(result.tm_hour)

    humidityDerate = cimisHumidity / localHumidity
    tempDerate = localTemp / cimisTemp
    ET0 = cimisET * (tempDerate * humidityDerate)

    print("ET0: ", ET0)

    # get gallons of water needed per hour (using gallons needed per day formula divided by 24)
    gallons = ((ET0 * pf * sqft *conversion) / IE) / 24
    #gallons = 3 * gallons
    print("Gallons Needed: ", gallons)

    # get time to run irrigation in minutes
    # gallons needed / (gallons per min)
    irrigationTime = gallons / systemRate
    print("Irrigation Time: ", irrigationTime)

    # signal relay to turn on
    Relay.systemState = True
    t = None
    print("starting Relay/Motor thread")
    t = threading.Thread(target=Relay.loop)
    t.daemon = True
    t.start()

    # open file to store information for the hour
    date = str(result.tm_mon)+'/'+str(result.tm_mday)+'/'+str(result.tm_year)
    t = str(result.tm_hour)+':'+str(result.tm_min)+'.'+str(result.tm_sec)
    #row = ['Date', 'Time', 'Local ET0', 'Local Humidity', 'Local Temp (F)', 'CIMIS ET0', 'CIMIS Humidity', 'CIMIS Temp (F)', 'Gallons Needed (gal/hr)', 'Time Needed (min)']
    row2 = [date, t, str(ET0), str(localHumidity), str(localTemp), str(cimisET), str(cimisHumidity), str(cimisTemp), str(gallons), str(irrigationTime)]

    with open('output.csv', mode='a') as outputFile:
        outputWriter = csv.writer(outputFile)
        #outputWriter.writerow(row)
        outputWriter.writerow(row2)

    outputFile.close()


def loop():
    global hour
    global localHumidity
    global localTemp
    global display

    
    row = ['Date (MM/DD/YYYY)','Time','Local ET0', 'Local Humidity', 'Local Temp(F)', 'CIMIS ET0', 'CIMIS Humidity', 'CIMIS Temp (F)', 'Gallons Needed (gal/hr)', 'Time Needed (min)']

    with open('output.csv', mode='a') as outputFile:
        outputWriter = csv.writer(outputFile)
        outputWriter.writerow(row)

    outputFile.close()

    dht = DHT.DHT(thermoPin)        # creates DHT class object
    count = 0                       # initialize minute count for an hour

    while(True):
        chk = dht.readDHT11()
        print("Check DHT: ", chk)

        # CONVERT CELSIUS TO FAHRENHEIT
        if (chk is dht.DHTLIB_OK):
            # if the start of an hour, do not need to average 2 values
            if (localHumidity == 0 and localTemp == 0):
                localHumidity = dht.humidity
                localTemp = 32 + (1.8*dht.temperature)
            # otherwise avergae the new data with the past averages of the hour
            else:
                localHumidity = (localHumidity + dht.humidity)/2
                localTemp = (localTemp + (32+(1.8*dht.temperature)))/2
        
        count += 1
        print("Local Humidity: ", localHumidity)
        print("Local Temperature: ", localTemp)
        display = True #enable LCD to display
        
        # check CIMIS for new data
        # if there is new data for the hour
        result = time.localtime(time.time())
        if (count >= 5 or result.tm_min == 59):
            getIrrigationTime()

            localHumidity = 0
            localTemp = 0
            count = 0
        
        # sleep for 1 minute
        time.sleep(60)
        display = False #disable LCD to display
        time.sleep(0.6)


import threading
import time
import RPi.GPIO as GPIO
import Freenove_DHT as DHT
import Relay

thermoPin = 11
localHumidity = [0.0,0.0,0.0]
localTemp = [0.0,0.0,0.0]
hour = 0
irrigationTime = 0.0
sqft = 200          # 200 square feet to be irrigated
pf = 1.0            # plant factor for lawn
conversion = 0.62   # constant conversion factor
IE = 0.75           # irrigation efficiency (suggested to use 0.75)
systemRate = 17     # 17 gallons per minute = 1020 gallons per hour
ET0 = 0
cimisHumidity = [0, 0, 0]
cimisTemp = [0, 0, 0]
cimisET = [0, 0, 0]

display = False

def getIrrigationTime():
    global irrigationTime
    global ET0
    # get ET, humidity, and temp from CIMIS
    cimisHumidity = [76, 71, 65]
    cimisTemp = [61.3, 63.8, 66.8]
    cimisET = [0.01, 0.02, 0.03]

    # get humidty and temp derating factors 
    # get ET0 for the 3 hours using these factors and CIMIS ET
    for i in range(0, 2):
        humidityDerate = localHumidity[i] / cimisHumidity[i]
        tempDerate = localTemp[i] / cimisTemp[i]
        ET0 = ET0 + (cimisET[i] / (tempDerate * humidityDerate))

    print("ET0: ", ET0)

    # get gallons of water needed for 3 hours (using gallons needed per day formula divided by 24)
    gallons = ((ET0 * pf * sqft *conversion) / IE) / 24
    gallons = 3 * gallons
    print("Gallons Needed: ", gallons)

    # get time to run irrigation per hour
    irrigationTime = gallons / systemRate
    print("Irrigation Time: ", irrigationTime)

    # signal relay to turn on
    Relay.systemState = True
    t = None
    print("starting Relay/Motor thread")
    t = threading.Thread(target=Relay.loop)
    t.daemon = True
    t.start()


def loop():
    global hour
    global localHumidity
    global localTemp
    global display

    dht = DHT.DHT(thermoPin)        # creates DHT class object
    count = 0                       # initialize minute count for an hour

    while(True):
        chk = dht.readDHT11()
        print("Check DHT: ", chk)

        if (chk is dht.DHTLIB_OK):
            # if the start of an hour, do not need to average 2 values
            if (localHumidity[hour] == 0 and localTemp[hour] == 0):
                localHumidity[hour] = dht.humidity
                localTemp[hour] = dht.temperature
            # otherwise avergae the new data with the past averages of the hour
            else:
                localHumidity[hour] = (localHumidity[hour] + dht.humidity)/2
                localTemp[hour] = (localTemp[hour] + dht.temperature)/2
        
        count += 1
        # check CIMIS for new data
        # if there is new data for the hour
        if (count == 1 and hour == 2):
            getIrrigationTime()

            # clear the past 3 hours of data
            for i in range (0, 2):
                localHumidity[i] = 0
                localTemp[i] = 0

        print("Local Humidity: ", localHumidity[hour])
        print("Local Temperature: ", localTemp[hour])
        
        display = True #enable LCD to display
        # sleep for 1 minute
        time.sleep(10)
        display = False #disable LCD to display
        time.sleep(0.6)

        if (count >= 1):
            count = 0
            hour = (hour + 1) % 3

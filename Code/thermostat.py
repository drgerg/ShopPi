#!/usr/bin/env python3
#
# thermostat.py - DIY Heat/AC controller.
# Copyright (c) 2019,2020,2021 - Gregory Allen Sanders.

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os,sys,subprocess,configparser,time,signal,pickle,traceback,shopSQL,bme280,threading
import argparse,logging
from time import sleep
from collections import OrderedDict
import RPi.GPIO as GPIO
#
### - Main body of code starts here.
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
thermoHome = os.path.abspath(os.path.dirname(__file__))

####  PINS PICKLE: A pickle file called CurrentState.pkl holds data on the current state of 
####               the GPIO pins that control various part of the system.
####               We first have to see if the file exists, and if not, create it.
####               CurrentState.pkl contains a dictionary named 'Tpins' which is made by OrderedDict()
####               from the normal dictionary named 'pins'. OrderedDict() gives us a sorted dictionary.
##
# We need a dictionary called 'Tpins'. It either exists in 'CurrentState.pkl' or we have to create it from scratch.
# If CurrentState.pkl exists, load it and extract the Tpins dictionary from it.
if os.path.isfile(thermoHome + '/CurrentState.pkl'):
    try:
        with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
            Tpins = pickle.load(pinPik)
    except EOFError:
        logger.debug("In main(). Encountered an empty .pkl file.  Moving on without it.")
        os.remove(thermoHome + '/CurrentState.pkl')
        os.system('cp ' + thermoHome + '/InitialTpins.pkl ' + thermoHome + '/CurrentState.pkl')
        pass
else:
    os.system('cp ' + thermoHome + '/InitialTpins.pkl ' + thermoHome + '/CurrentState.pkl')
    with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
        Tpins = pickle.load(pinPik)
#
### NOW actually use the contents of the dictionary 'Tpins' to set the GPIO pins.
#
# To initialize the hardware to an 'Off' state, set each pin as an output and make it HIGH (HIGH = off):
for pin in Tpins:
    GPIO.setup(pin, Tpins[pin]['I-O'])
    GPIO.output(pin, Tpins[pin]['state'])
#
# Tpar is a dictionary that holds all of our working variables. As a dictionary, it's a 'keyword:value' pair
# file format. We'll use this to carry these variables around from place to place as 'kwargs'.
# Tpar is saved to disk in the 'thermParms.pkl' file.  The next two lines read that into memory.
with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
    Tpar = pickle.load(tpmR)
#
# showStatus() does what the name implies, it gathers info about the current state of affairs and 
# puts it in the log file as well as printing it to stdout.
def showStatus():
    tempC,probeTemp = shopSQL.getTemp('Probe1')
    logger = logging.getLogger(__name__)
    if os.path.isfile(thermoHome + '/CurrentState.pkl'):
        try:
            with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
                Tpins = pickle.load(pinPik)
        except EOFError:
            logger.debug("In main(). Encountered an empty .pkl file.  Moving on without it.")
            os.remove(thermoHome + '/CurrentState.pkl')
            pass
    for pin in Tpins:
        status = GPIO.input(pin)
        if status == 1:
            statStr = 'Off'
        if status == 0:
            statStr = 'On'
        logger.debug('Pin ' + str(pin) + ' ' + str(Tpins[pin]['name']) + ' is ' + statStr)
        print('Pin ' + str(pin) + ' ' + str(Tpins[pin]['name']) + ' is ' + statStr)
    logger.debug(probeTemp)
    print(probeTemp)
#
# newStat() is called when we want to change the status of outputs on the GPIO header.
#
def newStat(changePin, action):
    thermoHome = os.path.abspath(os.path.dirname(__file__))
    logger = logging.getLogger(__name__)
    if os.path.isfile(thermoHome + '/CurrentState.pkl'):
        try:
            with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
                Tpins = pickle.load(pinPik)
        except EOFError:
            logger.debug("In newStat(). Encountered an empty .pkl file.  Moving on without it.")
            os.remove(thermoHome + '/CurrentState.pkl') 
            pass
    # Convert the pin into an integer:
    changePin = int(changePin)
    # Get the device name for the pin being changed:
    deviceName = Tpins[changePin]['name']
    if action == "on":
        # Set the pin low. Toggle low pins high to keep only one low. HIGH is Off.:
        if changePin == 5:  # compressor
            GPIO.output(5, GPIO.LOW)
        if changePin == 18:  # Low Fan
            GPIO.output(22, GPIO.HIGH)
            GPIO.output(23, GPIO.HIGH)
            GPIO.output(25, GPIO.HIGH)
            GPIO.output(18, GPIO.LOW)
        if changePin == 22:  # Medium Fan
            GPIO.output(18, GPIO.HIGH)
            GPIO.output(23, GPIO.HIGH)
            GPIO.output(25, GPIO.HIGH)
            GPIO.output(22, GPIO.LOW)
        if changePin == 23:  # High Fan
            GPIO.output(18, GPIO.HIGH)
            GPIO.output(22, GPIO.HIGH)
            GPIO.output(25, GPIO.HIGH)
            GPIO.output(23, GPIO.LOW)
        if changePin == 25:  # Heater
            GPIO.output(18, GPIO.HIGH)
            GPIO.output(22, GPIO.HIGH)
            GPIO.output(23, GPIO.HIGH)
            GPIO.output(25, GPIO.LOW)
        if changePin == 24:  # Power (VCC for airconditioner internal circuits)
            GPIO.output(24, GPIO.LOW)
        message = "Turned " + deviceName + " on."

    if action == "off":      ## Put everything in a Off state.
        if changePin == 24:
            GPIO.output(5, GPIO.HIGH)
            GPIO.output(18, GPIO.HIGH)
            GPIO.output(22, GPIO.HIGH)
            GPIO.output(23, GPIO.HIGH)
            GPIO.output(24, GPIO.HIGH)
            GPIO.output(25, GPIO.HIGH)
            message = "System powered down."

        if changePin != 24:
            GPIO.output(changePin, GPIO.HIGH)
            message = "Turned " + deviceName + " off."
    # For each pin, read the pin state and store it in the pins dictionary:
    for pin in Tpins:
        Tpins[pin]['state'] = GPIO.input(pin)
    logger.debug('Pin ' + str(changePin) + ' ' + deviceName + ' ' + action)
    with open(thermoHome + '/CurrentState.pkl', 'wb+') as pinPikW:
        pickle.dump(Tpins, pinPikW, pickle.HIGHEST_PROTOCOL)
    logger.debug(message)
    return message


def shopEnv(semode,**Tpar):
    thermoHome = os.path.abspath(os.path.dirname(__file__))
    logger = logging.getLogger(__name__)
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    curSEM = (Tpar['SEMode'])
    logger.debug('Into shopEnv() with a current SEMode value of: ' + str(curSEM) + '. semode comes here as: ' + semode)
    # if curSEM != semode:
    if semode == 'cool':
        setCoolMode(**Tpar)
    if semode == 'off':
        setOffMode(**Tpar)
    if semode == 'dehum':
        setDehumMode(**Tpar)
    if semode == 'fan':
        setFanMode(3)
    if semode == 'heat':
        setHeatMode(**Tpar)
    Tpar['SEMode'] = semode
    newSET = (Tpar['SETemp'])
    newSEF = (Tpar['SEFan'])
    newSEM = Tpar['SEMode']
    # 
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    retStr = 'shopEnv() updated settings. Mode: ' + newSEM + ' Temp: ' + str(newSET) + ' Fan: ' + str(newSEF) + '.'
    logger.debug(retStr)
    return retStr

##    CONTINUOUS LOOP THAT CHECKS TEMPERATURE EVERY 10 SECONDS
##    AND TRIGGERS CHANGES BASED ON RESULTS.
##    The variables are: SE and ST followed by a operational term 'Mode, Temp, Fan'.
##    SEMode is 'Shop Environment Mode'. It is what the user called for. This stays constant until another mode is selected.
##    STMode is 'STatus - Mode'.  It shows what is active currently. This changes based on the actual status of the moment.
#
def readTempLoop(**Tpar):
    stopLoop = 0
    while stopLoop == 0:
        # Get the Tpar dictionary from thermParms.pkl
        with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
            Tpar = pickle.load(tpmR)
        logger.debug('Top of readTempLoop. \nTpar value: ' + str(Tpar))
        # Set up some local variables based on the contents of the Tpar dictionary
        SEModeL, STModeL = Tpar['SEMode'], Tpar['STMode']
        SETempL, STTempL = float(Tpar['SETemp']), float(Tpar['STTemp'])
        # If the SEt Mode variable is 'off' and the STatus Mode variable is NOT 'off', make it 'off.
        if SEModeL == 'off' and STModeL != 'off':
            STModeL = 'off'
        logger.debug('First Stats. SEModeL: ' + SEModeL + '. SETempL: ' + str(SETempL) + '. STModeL: ' + STModeL + '. STTempL: ' + str(STTempL) + '.')
        # Get Temperature, Pressure and Humidity from the BME280 sensor
        bmeTemp,bmepres,bmeHum,bmeXtraHum = bme280.readBME280All()
        # Put the BME280 values into human-useable form.
        tempF = float('{:.2f}'.format(float(9/5 * bmeTemp + 32.00)))
        humid = float('{:.2f}'.format(float(bmeHum)))
        logger.debug('Initial loop temperature TempF: ' + str(tempF))
        #
        ## COOLING MODE SECTION START
        #
        if SEModeL=='cool':
            logger.debug('SEModeL was "cool" so we came here.')
            # It's hotter than the SEt temperature, SEt Mode is 'cool', AND STatus Mode is NOT 'cool'.
            if tempF >= SETempL and SEModeL == 'cool' and STModeL != 'cool':
                logger.debug(' . . . Cool. Caught by first if . . . ')
                # Make sure STatus temperature variable is 3 degrees cooler than SEt temp variable.
                # That then becomes the target temp at which the compressor is turned off.
                if STTempL != SETempL - 3:
                    STTempL = SETempL - 3
                logger.debug('Airconditioner was just turned on. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
                # 
                # Run setCoolMode() with the Tpar dictionary as keyword arguments (kwargs) and return here.
                scmVar = setCoolMode(**Tpar)
                # Update the STatus Mode variable with what returned from setCoolMode(). Hint: it should be 'cool'.
                Tpar['STMode'] = scmVar
                # Populate cmSEM variable from Tpar's SEt Mode value.
                cmSEM = Tpar['SEMode']
                logger.debug('setCoolMode() set STMode to : ' + scmVar + '. SEMode is: ' + cmSEM + '.')
                # The end result should be SEMode: 'cool', STMode: 'cool', SETemp is higher than tempF, 
                # and STTemp is 3 degrees lower than SETemp.
                # Next time this cycles around, this IF block gets skipped because STMode IS 'cool'.
            if SEModeL == 'cool' and STTempL!= SETempL - 3:
                logger.debug(' - - - Cool. Caught by second if - - - ')
                logger.debug('SETempL: ' + str(SETempL) + ' STTempL: ' + str(STTempL))
                STTempL = SETempL - 3
                Tpar['STTemp'] = str(STTempL)

            if tempF <= STTempL and SEModeL == 'cool' and STModeL == 'cool':
                logger.debug(' + + + Cool. Caught by third if + + + ')
                if SETempL != STTempL + 3:
                    SETempL = STTempL + 3
                    Tpar['SETemp'] = str(SETempL)
                STModeL = 'off'
                logger.debug('Airconditioner is being turned off. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
                Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
                Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
                Tpar = setOffMode(**Tpar)

            if tempF <= STTempL and SEModeL == 'cool' and STModeL != 'cool':
                logger.debug(' + + + Cool. Caught by fourth if + + + \nSEModeL is cool, STModeL is NOT cool.')
                if SETempL != STTempL + 3:
                    SETempL = STTempL + 3
                    Tpar['SETemp'] = str(SETempL)
                logger.debug('Airconditioner is off, but mode is cool. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
                Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
                Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
                if STModeL != 'off':
                    Tpar = setOffMode(**Tpar)
        #
        ## HEAT MODE SECTION START
        #
        if SEModeL == 'heat':
            logger.debug('SEModeL was "heat" so we came here.')
            # Check to see if the heater pin is in the wrong state, which can happen after a service restart.
            if STModeL == 'heat' and GPIO.input(25) == 1:
                setHeatMode(**Tpar)
                logger.debug("Caught the heater pin HIGH. Must have been a service restart. Fixed it.")
            # Now we go on about our normal business of monitoring the temperature and responding.
            if tempF <= SETempL and SEModeL == 'heat' and STModeL != 'heat':
                logger.debug(' . . . Heat. Caught by first if . . . ')
                if STTempL != SETempL + 3:
                    STTempL = SETempL + 3
                logger.debug('Heater was just turned on. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
                Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
                Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
                shmVar = setHeatMode(**Tpar)
                Tpar['STMode'] = shmVar
                cmSEM = Tpar['SEMode']
                logger.debug('setHeatMode() set SEMode to : ' + cmSEM + '.')
            if SEModeL == 'heat' and STTempL!= SETempL + 3:
                logger.debug(' - - - Heat. Caught by second if - - - ')
                STTempL = SETempL + 3
                Tpar['STTemp'] = str(STTempL)
                logger.debug('STTemp adjusted upward in Tpar')
            if tempF >= STTempL and SEModeL == 'heat' and STModeL == 'heat':
                logger.debug(' + + + Heat. Caught by third if + + + ')
                if SETempL != STTempL - 3:
                    SETempL = STTempL - 3
                    Tpar['SETemp'] = str(SETempL)
                STModeL = 'off'
                logger.debug('Heater is being turned off. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
                Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
                Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
                Tpar = setOffMode(**Tpar)

        sleep(10)

#
##    ONE-OFF ONE-SHOT FUNCTIONS BELOW HERE    ##
#

def setCoolMode(**Tpar):
    logger = logging.getLogger(__name__)
    newStat(24,'on')
    newStat(23,'on')
    newStat(5,'on')
    Tpar['STMode'] = 'cool'
    Tpar['STFan'] = 'on'
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    logger.debug('Cool Mode Set.')
    scmVar = Tpar['STMode']
    return scmVar

def setHeatMode(**Tpar):
    logger = logging.getLogger(__name__)
    newStat(25,'on')
    Tpar['STMode'] = 'heat'
    Tpar['STFan'] = 'off'
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    logger.debug('Heat Mode Set.')
    logger.debug(str(Tpar))
    shmVar = Tpar['STMode']
    return shmVar

def setDehumMode(**Tpar):
    SEMode = Tpar['SEMode']

def setOffMode(**Tpar):
    logger = logging.getLogger(__name__)
    SEMode = Tpar['SEMode']
    STMode = Tpar['STMode']
    SETemp = Tpar['SETemp']
    logger.debug('Inside setOffMode(), SETemp is: ' + str(SETemp))
    SEFan = Tpar['SEFan']
    if SEMode == 'off':
        newStat(24,'off')
        Tpar['SEMode'] = 'off'
        Tpar['STMode'] = 'off'
        Tpar['SEFan'] = 0
    if SEMode == 'cool':
        newStat(5,'off')
        newStat(23,'off')
        newStat(22,'off')
        newStat(18,'off')
        Tpar['SEMode'] = 'cool'
        Tpar['STMode'] = 'off'
        Tpar['SEFan'] = 0
    if SEMode == 'heat':
        newStat(25,'off')
        Tpar['SEMode'] = 'heat'
        Tpar['STMode'] = 'off'
        Tpar['SEFan'] = 0
    SEMode = Tpar['SEMode']
    STMode = Tpar['STMode']
    SETemp = Tpar['SETemp']
    SEFan = Tpar['SEFan']
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    sleep(2)
    logger.debug('SetOffMode() - SEMode: ' + str(SEMode) + '. STMode: ' + str(STMode) + '. SETemp: ' + str(SETemp) + '. SEFan: ' + str(SEFan))
    return Tpar


def setTemp(setemp,**Tpar):
    logger = logging.getLogger(__name__)
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    logger.debug('Changing Temp setting from: ' + Tpar['SETemp'] + ' to ' + str(setemp) + '.')
    #print(Tpar['SETemp'])
    Tpar['SETemp'] = str(setemp)
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    newTempRtrn = (Tpar['SETemp'])
    return newTempRtrn

def setFanMode(SEFan,**Tpar):
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    if SEFan == 0:          # off
        newStat(5,'off')
        newStat(23,'off')
        newStat(22,'off')
        newStat(18,'off')
        Tpar['STFan'] = 0
    if SEFan == 1:          # low
        newStat(5,'off')
        newStat(18,'on')
        Tpar['STFan'] = 1
    if SEFan == 2:          # medium
        newStat(5,'off')
        newStat(22,'on')
        Tpar['STFan'] = 2
    if SEFan == 3:          # high
        newStat(5,'off')
        newStat(23,'on')
        Tpar['STFan'] = 3
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
#
##   END ONE-OFF SHOT FUNCTIONS   ##
#
#
### - Main body of code ends here.
#
#
##
### - Below here is code to use when this is run from the commandline.
##
#

if __name__ == "__main__":
    try:
        thermoHome = os.path.abspath(os.path.dirname(__file__))
        config = configparser.RawConfigParser()
        #
        parser = argparse.ArgumentParser()
        logger = logging.getLogger(__name__)
        parser.add_argument("-d", "--debug", help="Turn on debugging output to stderr", action="store_true")
        # define arguments first, then set the args variable.  Dunno why it matters, but it does.
        args = parser.parse_args()
        if args.debug:
            logging.basicConfig(filename=thermoHome + '/shopLog.log', format='[%(name)s]:%(levelname)s: %(message)s. - %(asctime)s', datefmt='%D %H:%M:%S', level=logging.DEBUG)
            logging.info("Debugging output enabled")
        else:
            logging.basicConfig(filename=thermoHome + '/shopLog.log', format='%(asctime)s - %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', level=logging.INFO)
        def SignalHandler(signal, frame):
            if signal == 2:
                sigStr = 'CTRL-C'
                logger.debug(' - - - - - -  thermostat.py - ' + sigStr + ' caught. - - - - - - ')
            with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
                Tpar = pickle.load(tpmR)
            setOffMode(**Tpar)
            with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
                pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
            logger.debug("Shutting down gracefully")
            logger.debug("Wrote to log in SignalHandler")
            logger.debug("That's all folks.  Goodbye")
            logger.debug(" - - - - thermostat.py DATA LOGGING STOPPED BY DESIGN - - - - ")
            logging.shutdown()
            sys.exit(0)
    
        signal.signal(signal.SIGINT, SignalHandler)  ## This one catches CTRL-C from the local keyboard
        signal.signal(signal.SIGTERM, SignalHandler) ## This one catches the Terminate signal from the system    
        logger.debug("Top of try")
        logger.debug(" - - - - thermostat.py DATA LOGGING STARTED - - - - ")
        readTempLoop(**Tpar)

    except Exception:
        logger.debug("Exception caught at bottom of try.", exc_info=True)
        error = traceback.print_exc()
        logger.debug(error)
        logger.debug("That's all folks.  Goodbye")
        logger.debug(" - - - -thermostat.py DATA LOGGING STOPPED BY EXCEPTION - - - - ")

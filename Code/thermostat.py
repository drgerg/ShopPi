#!/usr/bin/env python3
#
# thermostat.py - DIY Heat/AC controller.
# Copyright (c) 2019,2020 - Gregory Allen Sanders.

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
# We need to retrieve 'Tpins'. It either exists in 'CurrentState.pkl' or we have to create it from scratch.
# If CurrentState.pkl exists, load it and extract the Tpins dictionary from it.
if os.path.isfile(thermoHome + '/CurrentState.pkl'):
    try:
        with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
            Tpins = pickle.load(pinPik)
    except EOFError:
        logger.info("In main(). Encountered an empty .pkl file.  Moving on without it.")
        os.remove(thermoHome + '/CurrentState.pkl')
        os.system('cp ' + thermoHome + '/InitialTpins.pkl ' + thermoHome + '/CurrentState.pkl')
        pass
else:
    os.system('cp ' + thermoHome + '/InitialTpins.pkl ' + thermoHome + '/CurrentState.pkl')
    with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
        Tpins = pickle.load(pinPik)
#  Now we have our dictionary 'Tpins'.
### NOW actually use the contents of 'Tpins' to set the GPIO pins.
#
# To initialize the hardware to an 'Off' state, set each pin as an output and make it HIGH (HIGH = off):
for pin in Tpins:
    GPIO.setup(pin, Tpins[pin]['I-O'])
    GPIO.output(pin, Tpins[pin]['state'])

with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
    Tpar = pickle.load(tpmR)

def showStatus():
    tempC,probeTemp = shopSQL.getTemp('Probe1')
    logger = logging.getLogger(__name__)
    if os.path.isfile(thermoHome + '/CurrentState.pkl'):
        try:
            with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
                Tpins = pickle.load(pinPik)
        except EOFError:
            logger.info("In main(). Encountered an empty .pkl file.  Moving on without it.")
            os.remove(thermoHome + '/CurrentState.pkl')
            #print('The empty .pkl file should be gone now.')
            pass
    for pin in Tpins:
        status = GPIO.input(pin)
        if status == 1:
            statStr = 'Off'
        if status == 0:
            statStr = 'On'
        logger.info('Pin ' + str(pin) + ' ' + str(Tpins[pin]['name']) + ' is ' + statStr)
        print('Pin ' + str(pin) + ' ' + str(Tpins[pin]['name']) + ' is ' + statStr)
    logger.info(probeTemp)
    print(probeTemp)
    #print('Bottom of showStatus()')
    # return Tpins

def newStat(changePin, action):
    thermoHome = os.path.abspath(os.path.dirname(__file__))
    logger = logging.getLogger(__name__)
    if os.path.isfile(thermoHome + '/CurrentState.pkl'):
        try:
            with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
                Tpins = pickle.load(pinPik)
            # Tpins = pickle.load(open(thermoHome + '/CurrentState.pkl', 'rb'))
        except EOFError:
            logger.info("In newStat(). Encountered an empty .pkl file.  Moving on without it.")
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
        if changePin == 24:  # Power 
            GPIO.output(24, GPIO.LOW)
        message = "Turned " + deviceName + " on."

    if action == "off":                 ## Put everything in a Off state.
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
    logger.info('Pin ' + str(changePin) + ' ' + deviceName + ' ' + action)
    with open(thermoHome + '/CurrentState.pkl', 'wb+') as pinPikW:
        pickle.dump(Tpins, pinPikW, pickle.HIGHEST_PROTOCOL)
    # pickle.dump(Tpins, open(thermoHome + '/CurrentState.pkl', 'wb'), pickle.HIGHEST_PROTOCOL)
    return message

def shopEnv(semode,**Tpar):
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    #print(Tpar['SEMode'])
    #print(Tpar['SETemp'])
    #print(Tpar['SEFan'])
    Tpar['SEMode'] = semode
    # if str(setemp) != '-':
    #     Tpar['SETemp'] = str(setemp)
    # if str(sefan) != '-'
    #     Tpar['SEFan'] = str(sefan)
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    newSEM = (Tpar['SEMode'])
    print(newSEM)
    if newSEM != semode:
        if newSEM == 'cool':
            setCoolMode()
        if newSEM == 'off':
            setOffMode()
        if newSEM == 'heat':
            setHeatMode()
        if newSEM == 'dehum':
            setDehumMode()
        if newSEM == 'fan':
            setFanMode(3)
        if newSEM == 'heat':
            setHeatMode()
            logger.info("shopEnv function called setHeatMode().")
    newSET = (Tpar['SETemp'])
    newSEF = (Tpar['SEFan'])
    # 
    retStr = 'shopEnv() updated settings. Mode: ' + newSEM + ' Temp: ' + str(newSET) + ' Fan: ' + str(newSEF) + '.'
    return retStr

##    CONTINUOUS LOOP CHECKING TEMP EVERY 10 SECONDS
##    AND THREADED TRIGGERING CHANGES BASED ON RESULTS.
##    The variables are: SE and ST followed by a operational term 'Mode, Temp, Fan'.
##    SEMode is 'Shop Environment Mode'. It is what the user called for.
##    STMode is 'STatus - Mode'.  It shows what is active currently.
#
def readTempLoop(**Tpar):
    stopLoop = 0
    while stopLoop == 0:
        # Retrieve our variables from the pickle file.  They are stored in a dictionary called Tpar.
        with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
            Tpar = pickle.load(tpmR)
        # print(Tpar)
        SEModeL, STModeL = Tpar['SEMode'], Tpar['STMode']  
        # The 'L' added to the variable means it is a Local variant of the named variable.
        # We'll use these L variants to mess with, then add them to the dictionary 'Tpar' later. 
        SETempL, STTempL = float(Tpar['SETemp']), float(Tpar['STTemp'])
        # First thing: If the user has asked for 'off' Mode, set the L variant to 'off'.
        if SEModeL == 'off' and STModeL != 'off':
            STModeL = 'off'
            print('Set STModeL to off')
        print('SEModeL: ' + SEModeL + ' SETempL: ' + str(SETempL) + ' STModeL: ' + STModeL + ' STTempL: ' + str(STTempL) + '.')
        bmeTemp,bmepres,bmeHum,bmeXtraHum = bme280.readBME280All()
        #print('temp retrieved')
        tempF = float('{:.2f}'.format(float(9/5 * bmeTemp + 32.00)))
        humid = float('{:.2f}'.format(float(bmeHum)))
        #print('format conversions done')
        # The following three 'if' statements check for three things:
            # 1) The user asked for 'off' and our L variant Mode is 'off',
            # 2) The user asked for 'cool' and our L variant Mode is 'cool' AND the temp is 
            #  less than or equal to what the user asked for.
            # 3) 
        if tempF >= SETempL and SEModeL == 'cool' and STModeL != 'cool':
            print(' . . . caught by first if . . . ')
            if STTempL != SETempL - 3:
                STTempL = SETempL - 3
            logger.info('Airconditioner was just turned on. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
            Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
            Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
            #print('dictionary updated')
            # scmthrd = threading.Thread(target=setCoolMode,kwargs=Tpar)
            # scmthrd.start()
            print('Running setCoolMode.')
            scmVar = setCoolMode(**Tpar)
            Tpar['STMode'] = scmVar
            cmSEM = Tpar['SEMode']
            print('setCoolMode() set SEMode to : ' + cmSEM + '.')
        if SEModeL == 'cool' and STTempL!= SETempL - 3:
            print(' - - - Caught by second if - - - ')
            #print('SETempL: ' + str(SETempL) + ' STTempL: ' + str(STTempL))
            STTempL = SETempL - 3
            Tpar['STTemp'] = str(STTempL)
            #print('STTemp updated in Tpar')
        if tempF <= STTempL and SEModeL == 'cool' and STModeL == 'cool':
            print(' + + + caught by third if + + + ')
            if SETempL != STTempL + 3:
                SETempL = STTempL + 3
                Tpar['SETemp'] = str(SETempL)
            # SEModeL = 'off'
            STModeL = 'off'
            logger.info('Airconditioner is being turned off. Set Temp: ' + str(SETempL) + ', target temp: ' + str(STTempL))
            Tpar['SEMode'], Tpar['STMode'] = SEModeL, STModeL
            Tpar['SETemp'], Tpar['STTemp'] = str(SETempL), str(STTempL)
            print('Running setOffMode().')
            Tpar = setOffMode(**Tpar)
        with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
            pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
        sleep(10)

#
##    ONE-OFF ONE-SHOT FUNCTIONS BELOW HERE    ##
#

def setCoolMode(**Tpar):
    newStat(24,'on')
    newStat(23,'on')
    newStat(5,'on')
    Tpar['STMode'] = 'cool'
    Tpar['STFan'] = 'on'
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    logger.info('Cool Mode Set.')
    scmVar = Tpar['STMode']
    return scmVar

def setHeatMode(**Tpar):
    SEMode = Tpar['SEMode']
    newStat(25,'on')
    Tpar['STMode'] = 'heat'
    Tpar['STFan'] = 'off'
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    logger.info('Heat Mode Set.')
    scmVar = Tpar['STMode']
    return scmVar

def setDehumMode():
    SEMode = Tpar['SEMode']

def setOffMode(**Tpar):
    logger = logging.getLogger(__name__)
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    SEMode = Tpar['SEMode']
    STMode = Tpar['STMode']
    SETemp = Tpar['SETemp']
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
    with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
        pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
    sleep(2)
    logger.info('SetOffMode() - SEMode: ' + str(SEMode) + ' SETemp: ' + str(SETemp) + ' SEFan: ' + str(SEFan))
    return Tpar


def setTemp(setemp,**Tpar):
    logger = logging.getLogger(__name__)
    with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        Tpar = pickle.load(tpmR)
    logger.info('Changing Temp setting from: ' + Tpar['SETemp'] + ' to ' + str(setemp) + '.')
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
    # return SEFanStat
#
##   END ONE-OFF SHOT FUNCTIONS   ##
#
##
### END BLOCK OF COPY/PASTE CODE FROM POOLPI
##
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
                logger.info(' - - - - - -  thermostat.py - ' + sigStr + ' caught. - - - - - - ')
            #print("SignalHandler invoked")
            Tpar = {'SEMode':'off', 'SETemp':'80', 'SEFan':'0', 'STMode':'off', 'STTemp':'80', 'STFan':'0'}
            setOffMode(**Tpar)
            with open(thermoHome + '/thermParms.pkl', 'wb+') as tpmW:
                pickle.dump(Tpar, tpmW, pickle.HIGHEST_PROTOCOL)
            logger.info("Shutting down gracefully")
            logger.debug("Wrote to log in SignalHandler")
            logger.info("That's all folks.  Goodbye")
            logger.info(" - - - - thermostat.py DATA LOGGING STOPPED BY DESIGN - - - - ")
            logging.shutdown()
            sys.exit(0)
    
        signal.signal(signal.SIGINT, SignalHandler)  ## This one catches CTRL-C from the local keyboard
        signal.signal(signal.SIGTERM, SignalHandler) ## This one catches the Terminate signal from the system    
        logger.debug("Top of try")
        # while True:
        logger.info(" - - - - thermostat.py DATA LOGGING STARTED - - - - ")
        # with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
        #     Tpar = pickle.load(tpmR)
        readTempLoop(**Tpar)

    except Exception:
        logger.info("Exception caught at bottom of try.", exc_info=True)
        error = traceback.print_exc()
        logger.info(error)
        logger.info("That's all folks.  Goodbye")
        logger.info(" - - - -thermostat.py DATA LOGGING STOPPED BY EXCEPTION - - - - ")

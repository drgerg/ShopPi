#!/usr/bin/env python3
#
""" shopSQL.py - Manage shopApp.py data logging.
    2019, 2020 - Gregory Allen Sanders"""

import os,sys,subprocess,configparser,logging,time,signal,mysql.connector,pickle,traceback,statistics,bme280,thermostat
from time import sleep
from mysql.connector import MySQLConnection, Error
import RPi.GPIO as GPIO
#
## ConfigParser init area.  Get some info out of working.conf.
#
#shopHome = os.getcwd()
shopHome = os.path.abspath(os.path.dirname(__file__))
config = configparser.RawConfigParser()
config.read(shopHome + '/shopApp.conf')
#
## End ConfigParser init

logger = logging.getLogger(__name__)

pklData = []
numBadPings = 0

def bme():

    s_outTemp = []
    s_pressure = []
    s_outHumidity = []
    s_rawHumidity = []
    tstart = time.time()

    while time.time() - tstart < 2:
        tempC,pres,humid,preHum = bme280.readBME280All()
        s_outTemp.append(tempC)
        s_pressure.append(pres)
        s_outHumidity.append(humid)
        s_rawHumidity.append(preHum)
    outTemp = statistics.mean(s_outTemp)
    pressure = statistics.mean(s_pressure)
    outHumidity = statistics.mean(s_outHumidity)
    extraHumid1 = statistics.mean(s_rawHumidity)

    return outTemp,pressure,outHumidity,extraHumid1

def getTemp(probe):

    probeSerial = config['Probes'][probe]
    probeName = config['ProbeNames'][probe + 'Name']
    probeAdjust = config['ProbeAdjust'][probe + 'Adjust']
    f = open('/sys/bus/w1/devices/' + probeSerial + '/w1_slave', 'r')
    line = f.readline()                 # read 1st line
    crc = line.rsplit(' ',1)
    crc = crc[1].replace('\n', '')
    if crc=='YES':
        line = f.readline()             # read 2nd line
        gettemp = line.rsplit('t=',1)
        gettemp = gettemp[1]
    else:
        gettemp = 99999
    f.close()
    tempC = (int(gettemp)/1000) + float(probeAdjust)
    tempF = '{:.2f}'.format(float(9/5 * tempC + 32.00))
    probeTemp = probeName +': ' + str(tempC) + '°C' + ' (' + str(tempF) + '°F)'

    return tempC,probeTemp

def datagrabber():
    tempC,probeTemp = getTemp('Probe1')
    shopTempF = '{:.2f}'.format(float(9/5 * tempC + 32.00))
    outTemp,pressure,outHumidity,extraHumid1 = bme()
    tempBMEF = '{:.2f}'.format(float(9/5 * outTemp + 32.00))
    humid = '{:.2f}'.format(float(outHumidity))
    ct = os.popen('vcgencmd measure_temp').readline()
    cpuRtn = ct.replace("temp=","").replace("'C\n","")
    cputemp1=float(cpuRtn)
    cputemp= '{:.2f}'.format(float(9/5 * cputemp1 + 32.00))
    return shopTempF,tempBMEF,humid,pressure,cputemp

#
##  mydb() COMPILE, CONTACT AND RECORD SHOP STATS TO MYSQL ON THE DATABASE SERVER
#
def mydb():
    global pklData,numBadPings
    # Get current values from all the sensors.
    shopTempF,tempBMEF,humid,pressure,cputemp = datagrabber()
    # Now make sure all the variables are of the right type.  Take no chances.
    shoptemp = float(shopTempF)
    tempbmef = float(tempBMEF)
    shophumid = float(humid)
    shoppress = float(pressure)
    shopcpu = float(cputemp)
    dtNow = int(time.time())
    dataTable = [dtNow,shoptemp,tempbmef,shophumid,shoppress,shopcpu]            # Put all the readings into a list.
    if os.path.exists(shopHome + '/shopData.pkl'):            ## This .pkl file will exist if the upcoming ping test failed last time around.
        pklData = pickle.load(open(shopHome + '/shopData.pkl', 'rb'))
    pklData.append(dataTable)                                 ## Merge the recent data with the .pkl file data just in case we are still offline
    logger.debug('dataTable was appended to pklData')
    DBhost=config.get('mySQL','Address')                      # get the mySQL login data from our config file.
    DBuser=config.get('mySQL','User')
    DBpasswd=config.get('mySQL','Password')
    DBdatabase=config.get('mySQL','Database')
    DBtable=config.get('mySQL','Table1')
    # Don't stop now . . . keep going!!!
    ## Check to see if we can ping the machine mySQL is running on
    pingRes = subprocess.call(['/bin/ping', '-c', '1', DBhost], stdout=subprocess.DEVNULL)  ## Ping test to make sure the SQL machine is there.
    logger.debug("Ping for server returned: " + str(pingRes))
    if pingRes == 0:                                        # We are connected.  Move ahead.  If not, don't do any of this stuff.
        if numBadPings > 0:
            logger.info("Connection to SQL server machine restored.")
        numBadPings = 0                                     # Prep the data, and send it to the SQL machine.
        for row in pklData:                                 # Normally there will only be one row. UNLESS the network was down, 
            dtNow = row[0]                                  # in which case there can be many.
            shoptemp = row[1]
            tempbmef = row[2]
            shophumid = row[3]
            shoppress = row[4]
            shopcpu = row[5]
            DTNhuman = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(dtNow))
            logger.info(DTNhuman + ' PT:' + str(format(shoptemp,'.2f')) + ' T:' + str(format(tempbmef,'.2f')) + ' H:' + str(format(shophumid,'.2f')) + ' P:' + str(format(shoppress,'.2f')) + ' C:' + str(format(shopcpu,'.2f')))
######  TEMPORARY CODE SECTION BELOW  #########################################
            # if float(tempbmef) >= 79.0:
            #     thermostat.shopEnv('cool',77,3)
            #     logger.info('From shopSQL.py, mydb() Turned AC On.')
            # if float(tempbmef) < 77.0:
            #     thermostat.shopEnv('off',77,3)
            #     logger.info('From shopSQL.py, mydb() Turned AC Off.')
######  TEMPORARY CODE SECTION ABOVE  ########################################
            try:
                                                            # prepare the database connector 
                mydb = mysql.connector.connect(
                    host=DBhost,
                    user=DBuser,
                    passwd=DBpasswd,
                    database=DBdatabase
                )
                cursor = mydb.cursor()                      # Attempt a connection with the remote database. If it is not there, 
                cursor.execute("select database();")        # an exception will be logged and we will save our data for the 
                record = cursor.fetchone()                  # next go-round.
                logger.debug("Got the database: " + str(record))
                addRecord = ('INSERT INTO ' + DBdatabase + '.' + DBtable + '' \
                    ' (dateTime,shopTemp,shopTempBME,shopHumidity,shopPress,shopCPU)' \
                    ' VALUES (%s,%s,%s,%s,%s,%s)')
                addData = (dtNow,shoptemp,tempbmef,shophumid,shoppress,shopcpu)
                logger.debug(addRecord %addData)
                cursor.execute(addRecord,addData)
                cursor.execute("SELECT * FROM " + DBdatabase + '.' + DBtable + " where id=(select max(id) from " + DBdatabase + '.' + DBtable + ")")
                record = cursor.fetchone()
                logger.debug('The last record contains: ' + str(record))
                mydb.commit()
                cursor.close()
                mydb.close()
                pklData = []                                ## RESET pklData to an empty list.
                if os.path.exists(shopHome + '/shopData.pkl'):
                    os.remove(shopHome + '/shopData.pkl')
                    logger.debug("shopData.pkl Pickle file erased.")
            except Exception:
                logger.info('Unable to connect with mySQL database.  Details to follow: ', exc_info=True)
                pass
            funNStr = sys._getframe().f_code.co_name
            logger.debug("Finished the " + funNStr + " function")
    else:                                                    # We are NOT CONNECTED.  Save our readings to a .pkl file
        logger.info("Ping test for SQL server machine failed.")
        numBadPings += 1
        pickle.dump(pklData, open(shopHome + '/shopData.pkl', 'wb+'), pickle.HIGHEST_PROTOCOL)
        logger.debug("shopData.pkl updated.")
        logger.info ("Number of bad pings is: " + str(numBadPings) + ".")
        if numBadPings >= 3:
            logger.info("Too many bad pings.  Setting up to reboot.")
            os.mknod(shopHome + '/rebootItNow')
        
def SignalHandler(signal, frame):
    if signal == 2:
        sigStr = 'CTRL-C'
        logger.info('* * * ' + sigStr + ' caught. * * * ')
    print("SignalHandler invoked")
    logger.info("Shutting down gracefully")
    logger.debug("Wrote to log in SignalHandler")
    logger.info("That's all folks.  Goodbye")
    logger.info(" - - - - shopSQL.py DATA LOGGING STOPPED BY DESIGN - - - - ")
    logging.shutdown()
    sleep(2)
    sys.exit(0)
    
if __name__ == "__main__":
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        import argparse

        ## Command line arguments parsing
        #
        parserSsql = argparse.ArgumentParser()
        parserSsql.add_argument("-d", "--debug", help="Turn on debugging output to stderr", action="store_true")
        argsssql = parserSsql.parse_args()
        if argsssql.debug:
            logging.basicConfig(filename=shopHome + '/shopLog.log', format='[%(name)s]:%(levelname)s: %(message)s - %(asctime)s', datefmt='%D %H:%M:%S', level=logging.DEBUG)
            logging.info("Debugging output enabled")
        else:
            logging.basicConfig(filename=shopHome + '/shopLog.log', format='%(asctime)s - %(message)s', datefmt='%a, %d %b %Y %H:%M:%S', level=logging.INFO)
        #
        ## End Command line arguments parsing

        signal.signal(signal.SIGINT, SignalHandler)  ## This one catches CTRL-C from the local keyboard
        signal.signal(signal.SIGTERM, SignalHandler) ## This one catches the Terminate signal from the system    


        if os.path.isfile(shopHome + '/CurrentState.pkl'):
            try:
                with open(shopHome + '/CurrentState.pkl', 'rb') as pinPik:
                    Tpins = pickle.load(pinPik)
            except EOFError:
                logger.info("In getTemp(). Encountered an empty .pkl file.  Moving on without it.")
                os.remove(shopHome + '/CurrentState.pkl')
                os.system('cp ' + shopHome + '/InitialTpins.pkl ' + shopHome + '/CurrentState.pkl')
                pass
        else:
            os.system('cp ' + thermoHome + '/InitialTpins.pkl ' + thermoHome + '/CurrentState.pkl')
            with open(thermoHome + '/CurrentState.pkl', 'rb') as pinPik:
                Tpins = pickle.load(pinPik)
            for pin in Tpins:
                GPIO.setup(pin, Tpins[pin]['I-O'])
                GPIO.output(pin, Tpins[pin]['state'])
            


        logger.debug("Top of try")
        while True:
            logger.info(" - - - - shopSQL.py DATA LOGGING STARTED - - - - ")
            freq=config.get('mySQL','LogFreq')
            goTime = time.time() + int(freq)
            while True:
                if time.time() < goTime:
                    time.sleep(1)
                else:
                    try:
                        goTime = time.time() + int(freq)
                        mydb()
                    except Error as error:
                        logger.info(error)
                    pass
        logger.info("Bottom of try")

    except Exception:
        logger.info("Exception caught at bottom of try.", exc_info=True)
        error = traceback.print_exc()
        logger.info(error)
        logger.info("That's all folks.  Goodbye")
        logger.info(" - - - -shopSQL.py DATA LOGGING STOPPED BY EXCEPTION - - - - ")
        logging.shutdown()
        sleep(2)
        sys.exit(0)

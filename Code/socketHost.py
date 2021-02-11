#!/usr/bin/env python3
#
# socketHost.py
#
# Cobbled together by Greg Sanders 2020 to be handle interrogation of the ShopPi system.
#
#     Copyright (c) 2019,2020 - Gregory Allen Sanders.

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

import socket,os,sys,traceback,ast,logging,signal,configparser,pickle,shopSQL,thermostat
from time import sleep



def main():
    host = ''
    port = 64444
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    thermoHome = os.path.abspath(os.path.dirname(__file__))
    try:
        s.bind((host, port))
    except socket.error as e:
        print(str(e))

    while True:
        try:
            s.listen(1)
            print('Waiting for a connection.')
            conn, addr = s.accept()
            # print('connected to: '+addr[0]+':'+str(addr[1]))
            # conn.send(str.encode('Welcome. Use "quit" to close connection.\n'))
        except Exception:
                traceback.print_exc(file=sys.stdout)
                incoming = 'An error was caught and displayed.'
                data = str.encode('It is time to part ways.')
                conn.sendall(data)
                pass

        while True:
            try:
                sockXferIn = conn.recv(2048)
                InCmd = pickle.loads(sockXferIn)
            except EOFError:
                logger.info("Encountered an empty .pkl file.  Moving on without it.")
                InCmd = 'break'
            logger.info('InCmd variable was populated from sockXferIn: ' + str(InCmd))
            print(str(InCmd))
##  BREAK
            if InCmd == 'break':
                pass
##  SET TEMPERATURE
            if InCmd == 'setTemp':
                newTempX = conn.recv(1024)
                newTemp = pickle.loads(newTempX)
                newTrtn = thermostat.setTemp(newTemp)
                packet = pickle.dumps(newTrtn)
                conn.sendall(packet)
                logger.info('Sent newTemp confirmation.')
##  HEAT
            if InCmd == 'heat':
                shStat = os.system('/home/greg/shop/thermSet.py -s0 -m heat ')
                logger.info('thermSet.py returned: ' + str(shStat))
                logger.info('From socketHost.py: ' + str(shStat))
##  COOL
            if InCmd == 'cool':
                shStat = os.system('/home/greg/shop/thermSet.py -s1 -m cool ')
                logger.info('thermSet.py returned: ' + str(shStat))
                logger.info('From socketHost.py: ' + str(shStat))
##  OFF
            if InCmd == 'off':
                shStat = os.system('/home/greg/shop/thermSet.py -m off -c0 -f0 -s0')
                with open(thermoHome + '/thermParms.pkl', 'rb') as tpmR:
                    Tpar = pickle.load(tpmR)
                Tpar = thermostat.setOffMode(**Tpar)
                shStat = Tpar['SEMode']
                logger.info('setOffMode() returned: ' + str(shStat))
##  SEND PINS
            if InCmd == 'sendPins':
                print('Received request for Pins.')
                Pins = (sockHome + '/CurrentState.pkl')
                with open(Pins, 'rb') as sendPins:
                    packet = sendPins.read(2048)
                    conn.sendall(packet)
                logger.info('Sent CurrentState.pkl')
##  THERMPARMS
            if InCmd == 'thermParms':
                print('Received request for Tpar contents.')
                Tpar = (sockHome + '/thermParms.pkl')
                with open(Tpar, 'rb') as sendTpar:
                    packet = sendTpar.read(2048)
                    conn.sendall(packet)
                logger.info('Sent thermParms.pkl')
##  SHOPENV
            if InCmd == 'shopEnv':
                print('Received request for environmental stats.')
                # shopTempF,tempBMEF,humid,pressure,cputemp = shopSQL.datagrabber()
                shopEnvStats = shopSQL.datagrabber()
                print(shopEnvStats)
                packet = pickle.dumps(shopEnvStats)
                conn.sendall(packet)
                logger.info('Sent shop environment stats.')
            try:
                conn.shutdown(1)
                conn.close()
                logger.info('Connection from ' + str(addr[0]) + ' closed.')
                break
            # except Exception:
            #     traceback.print_exc(file=sys.stdout)
            #     incoming = 'An error was caught and displayed.'
            except OSError:
                break
     #
            if not sockXferIn:
                try:
                    conn.shutdown(1)
                    conn.close()
                    logger.info('Connection closed.')
                    break
                # except Exception:
                    # traceback.print_exc(file=sys.stdout)
                    # incoming = 'An error was caught and displayed.'
                except OSError:
                    break
    #
        conn.close()
    else:
        print('All Finished.')
        pass

def SignalHandler(signal, frame):
        logger.info("- - - - - - - - - - - Cleaning up - - - - - - - - - - - - - - - ")
        logger.info("Shutting down gracefully")
        logger.debug("This is SignalHandler")
        logger.info("Displayed .info and .debug in SignalHandler")
        logger.info("Shutdown initiated")
        logger.debug("Wrote to log in SignalHandler")
        sys.exit(0)


if __name__ == "__main__":
        try:
            import argparse
            ## Init area.  configparser and logger
            #
            sockHome = os.path.abspath(os.path.dirname(__file__))
            config = configparser.RawConfigParser()
            config.read(sockHome + '/sock.conf')
            logger = logging.getLogger(__name__)

            ## Command line arguments parsing
            #
            parsersm = argparse.ArgumentParser()
            parsersm.add_argument("-d", "--debug", help="Turn on debugging output to stderr", action="store_true")
            argssm = parsersm.parse_args()
            if argssm.debug:
                logging.basicConfig(filename=sockHome + '/sock.log', format='[%(name)s]:%(levelname)s: %(message)s. - %(asctime)s', datefmt='%D %H:%M:%S', level=logging.DEBUG)
                logging.info("Debugging output enabled")
            else:
                logging.basicConfig(filename=sockHome + '/sock.log', format='%(asctime)s - %(message)s.', datefmt='%a, %d %b %Y %H:%M:%S', level=logging.INFO)
            #
            ## End Command line arguments parsing
            logger.info(" - - - - - - - - - - - STARTING socketHost.py NORMALLY - - - - - - - - - - - - - - ")
            signal.signal(signal.SIGINT, SignalHandler)
            logger.debug("Top of try")
            main()
            logger.info("Bottom of try")

        except  ValueError as errVal:
            print(errVal)
            pass
        logger.info("That's all folks.  Goodbye")


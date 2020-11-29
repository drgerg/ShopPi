#!/usr/bin/env python3
#
# A utility by Greg Sanders to set the initial state and save that into a pickle file.
# This utility creates a file named 'InitialTpins.pkl'.  If you want to reset the 
# initial settings, you will need to stop the shopThermo.service and delete 'CurrentState.pkl'.
# When you restart shopThermo.service, it'll load 'InitialTpins.pkl' into 'CurrentState.pkl'.
# To make an edit to InitialTpins.pkl, uncomment everything below "import os,pickle" and run './InitializePickle.py'.
# Afterwards, re-comment that block.  Then you can run it to set 'thermParms.pkl' only.
#
import os,pickle
# from collections import OrderedDict
# import RPi.GPIO as GPIO
# GPIO.setmode(GPIO.BCM)
# GPIO.setwarnings(False)
# thermoHome = os.path.abspath(os.path.dirname(__file__))
# pins = {
#     18 : {'sort' : '1', 'name' : 'Fan Low', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH},
#     22 : {'sort' : '2', 'name' : 'Fan Medium', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH},
#     23 : {'sort' : '3', 'name' : 'Fan High', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH},
#     5 : {'sort' : '4', 'name' : 'Compressor', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH},
#     24 : {'sort' : '5', 'name' : 'Power', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH},
#     25 : {'sort' : '6', 'name' : 'Heat', 'I-O' : GPIO.OUT, 'state' : GPIO.HIGH}
#     }
#             # SAVE THIS DICTIONARY AS AN ORDERED DICTIONARY USING OrderedDict()
# Tpins = OrderedDict(sorted(pins.items(), key=lambda kv: kv[1]['sort']))
#             # SAVE THE NEW ORDERED DICTIONARY TO 'CurrentState.pkl'
# with open(thermoHome + '/InitialTpins.pkl', 'wb+') as pinPikW:
#     pickle.dump(Tpins, pinPikW, pickle.HIGHEST_PROTOCOL)
# # To initialize the hardware to an 'Off' state, set each pin as an output and make it HIGH (HIGH = off):
# for pin in Tpins:
#     GPIO.setup(pin, Tpins[pin]['I-O'])
#     GPIO.output(pin, Tpins[pin]['state'])

Tpar = {'SEMode':'off', 'SETemp':'80', 'SEFan':'0', 'STMode':'off', 'STTemp':'77', 'STFan':'0'}
with open(thermoHome + '/thermParms.pkl', 'wb+') as pinPikW:
    pickle.dump(Tpar, pinPikW, pickle.HIGHEST_PROTOCOL)
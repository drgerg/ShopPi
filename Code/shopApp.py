#!/usr/bin/env python3
'''
shopApp.py

Adapted by Greg Sanders December 2019 to monitor conditions in my shop.
    Adapted from: https://github.com/casspop/shopControls
       which is, of course, itself an adaptation.  See that project for attribution.

'''

import RPi.GPIO as GPIO
import os, pickle, re, time, datetime, requests, subprocess, shopGetSensors, configparser, signal, threading, dht11, shopGetSensors
from collections import OrderedDict
from flask import Flask, render_template, request, flash, url_for
from flask_wtf import FlaskForm
from wtforms import TextField, TextAreaField, BooleanField, StringField, IntegerField, SubmitField, validators
from wtforms.validators import Length, DataRequired, NumberRange
#from graph import build_graph
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '47thousandFineFroGGiesH099ingMerilythru4&3'
print(app)
#
## Get the HOME environment variable
#
shopAppHome = os.path.abspath(os.path.dirname(__file__))

#
## ConfigParser init area.  Get some info out of 'shopApp.conf'.
#
config = configparser.RawConfigParser()
config.read(shopAppHome + '/shopApp.conf')
#
## End ConfigParser init
#

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(True)


@app.route('/')
def main():
   tPin = config.get('Pins','PinA')
   templateData = {
      'pin' : tPin
      }
   #
   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)
#
## SET UP FOR THE STATS VIEW
#
@app.route('/stats/')
def stats():
   tPin = config.get('Pins','PinA')
   probe1Nom = config.get('Probes','Probe1')
   probe1Temp = shopGetSensors.getTemp(probe1Nom,tPin)
   #
   # Put the various temps dictionary into the template data dictionary:
   #
   templateData = {
      'pin' : tPin,
      'probe1Temp' : probe1Temp
      }
   #
   # Pass the template data into the template main.html and return it to the user
   return render_template('stats.html', **templateData)

#   pickle.dump(Spins, open(shopAppHome + '/CurrentState.pkl', 'wb'), pickle.HIGHEST_PROTOCOL)
   # Save the current schedule to our .pkl file.
#   pickle.dump(sched1, open(shopAppHome + '/CurrentSched.pkl', 'ab+'), pickle.HIGHEST_PROTOCOL)
#   return render_template('main.html', **templateData)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
    #app.run(host='0.0.0.0', port=9000, debug=True)
    #app.run(host='192.16.1.10', port=80)

# ShopPi
 ### Shop Environmental Controls and Sensors

This is the newest node in my little PiNet.  It's also the least finished of the group. You might think it's ugly, and you'd be mostly right.  I have no intention of caring how it looks, only how it works.

I used an early Pi B+ and a Elegoo 8-relay board along with a DS18B20 W1 temp probe and a BME280 for sensors.  The BME280 is the primary sensor, the W1 probe is zip tied to the front grill of the window unit and can act as a comparison temperature source.

I learned it's a lot more difficult writing software to control cooling and heating of a room than I thought.  Honestly, I'm not sure I've done a very good job of it, but the window unit works, and 'thermostat.py' does it's job.  

I am planning to make substantive improvements, and consider this to be in the 'alpha' stages of development at this time (Dec 2020).

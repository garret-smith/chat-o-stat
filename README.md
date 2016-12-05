# chat-o-stat
Google-talk enabled thermostat for remote (and local) control
of a milli-volt heater.

Thermostat set-point can be adjusted from the touchscreen or by chatting with
the thermostat over Google Talk.

Nice animated flames show when the heat is on.  Low [blue flames](bluefire.gif)
for the pilot light, large [orange-red flames](fire.gif) when the heat is on.

## Hardware
Runs on a [Raspberry P Model B+](http://www.adafruit.com/product/1914) with a
[PiTFT](http://www.adafruit.com/product/1601) display.

A [BMP180](http://www.adafruit.com/products/1603) sensor is connected to
the I2C port for measuring temperature.

A relay is connected to GPIO 7.

A USB WiFi module for connecting to the internet.

## Software
Base OS is the Adafruit-provided raspbian image with kernel module for PiTFT
framebuffer support.

Uses PyQt for the UI, Adafruit BMP library for reading temperature, sleekxmpp
for connecting to Google Talk servers, WiringPi for controlling the GPIO.

## notes
Setting the GPIO pin controlling the relay to output mode and setting logic
0/1 did not work for me.  The relay always saw a logic 1 and closed.  Instead,
to get the relay to recognize logic 0 I had to set the GPIO pin to input mode.
I probably could (should?) have solved this using a pull-down resistor,
but this worked for me.

## TODO
   * Clean things up
   * Put each class in it's own file


# chat-o-stat
Google-talk enabled thermostat for remote (and local) control of a milli-volt heater.

## Hardware
Runs on a [Raspberry P Model B+](http://www.adafruit.com/product/1914) with a [PiTFT](http://www.adafruit.com/product/1601) display.
A [BMP180](http://www.adafruit.com/products/1603) sensor is connected to the I2C port for measuring temperature.
A relay is connected to GPIO 1.
A USB WiFi module for connecting to the internet.

## Software
Uses PyQt for the UI


import logging
import threading

from enum import Enum
from subprocess import call

import config

Mode = Enum('Mode', 'On Off Thermostat')

class Thermostat():
    def __init__(self, temp, setTemp):
        self._hysteresis = config.hysteresis
        self._stateLock = threading.Lock()

        # each of these need to be observable variables
        # they could be changed by multiple threads
        # (UI / bot / temp poller) and UI needs notification
        # notification when they do
        self._temp = float(temp)
        self._setTemp = float(setTemp)
        self._mode = Mode.Thermostat
        self._heating = False
        self._toNotify = []

    def notify(self, dest):
        self._toNotify.append(dest)

    def setMode(self, newMode):
        if self._mode == newMode:
            return
        with self._stateLock:
            self._mode = newMode
            if self._mode == Mode.On:
                self.turnOn()
            elif self._mode == Mode.Off:
                self.turnOff()
            elif self._mode == Mode.Thermostat:
                self.checkAction()
            self.onMode()

    def setSetTemp(self, setTemp):
        if self._setTemp == setTemp:
            return
        with self._stateLock:
            self._setTemp = setTemp
            self.checkAction()
            self.onSetTemp()

    def setTemp(self, temp):
        if self._temp == temp:
            return
        with self._stateLock:
            self._temp = float(temp)
            self.checkAction()
        self.onTemp()

    def onMode(self):
        for n in self._toNotify:
            try:
                n.onMode(self._mode)
            except:
                logging.error("onMode %s failed", n, exc_info=True)

    def onSetTemp(self):
        for n in self._toNotify:
            try:
                n.onSetTemp(self._setTemp)
            except:
                logging.error("onSetTemp %s failed", n, exc_info=True)

    def onTemp(self):
        for n in self._toNotify:
            try:
                n.onTemp(self._temp)
            except:
                logging.error("onTemp %s failed", n, exc_info=True)

    def onHeating(self):
        for n in self._toNotify:
            try:
                n.onHeating(self._heating)
            except:
                logging.error("onHeating %s failed", n, exc_info=True)

    def getMode(self):
        return self._mode

    def getSetTemp(self):
        return self._setTemp

    def getTemp(self):
        return self._temp

    def checkAction(self):
        if self._mode == Mode.Thermostat:
            if self._heating:
                if self._temp > self._setTemp + self._hysteresis:
                    self.turnOff()
            else:
                if self._temp < self._setTemp - self._hysteresis:
                    self.turnOn()

    def turnOn(self):
        if not self._heating:
            self._heating = True
            call(["gpio", "mode", "7", "out"])
            logging.info("Turning heat ON")
            self.onHeating()

    def turnOff(self):
        if self._heating:
            self._heating = False
            call(["gpio", "mode", "7", "in"])
            logging.info("Turning heat OFF")
            self.onHeating()


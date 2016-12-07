# vim: et:sw=4:ts=4

import logging
import logging.config
import sys
import threading
import time
import traceback

from enum import Enum
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from subprocess import check_output,call

import Adafruit_BMP.BMP085 as BMP085

from Thermostat import Thermostat,Mode
from ThermostatGui import ThermostatGui
from ThermoBot import ThermoBot

from SqsBot import SqsBot
from StatusWriter import StatusWriter

from DebugGui import DebugGui
from DebugBot import DebugBot

import access_codes

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

class TempPollerThread(threading.Thread):
    def __init__(self, sensor, thermostat):
        super(TempPollerThread, self).__init__()
        self._sensor = sensor
        self._thermostat = thermostat

    def run(self):
        while True:
            tC = self._sensor.read_temperature()
            tF = tC * (9.0/5.0) + 32.0
            self._thermostat.setTemp(tF)
            time.sleep(1)

def start_thermostat(sensor, thermostat):
    logging.config.fileConfig('log.conf',disable_existing_loggers=0)
    logging.getLogger('Adafruit_I2C').setLevel(logging.WARN)
    logging.getLogger('Adafruit_BMP').setLevel(logging.WARN)

    # init the GPIO
    call(["gpio", "mode", "7", "in"])

    tPollerThread = TempPollerThread(sensor, thermostat)
    tPollerThread.start()

    chatbot = ThermoBot(access_codes.jid, access_codes.password, thermostat)
    chatbot.register_plugin('xep_0030') # Service Discovery
    chatbot.register_plugin('xep_0004') # Data Forms
    chatbot.register_plugin('xep_0060') # PubSub
    chatbot.register_plugin('xep_0199', {'keepalive': True, 'interval': 60, 'timeout': 15}) # XMPP Ping
    if chatbot.connect(('talk.google.com', 5222)):
        logging.info("logged in to talk.google.com")
        chatbot.process(block=False)
    else:
        logging.warning("login to talk.google.com failed")
        sys.exit(0)

    sqs_bot = SqsBot(thermostat)
    sqs_bot.start()

    status_writer = StatusWriter(thermostat)

    app = QApplication(sys.argv)
    theromstatUi = ThermostatGui(thermostat)

    sys.exit(app.exec_())

def start_debug(thermostat):
    chatbot = DebugBot(access_codes.jid, access_codes.password, thermostat)
    chatbot.register_plugin('xep_0030') # Service Discovery
    chatbot.register_plugin('xep_0004') # Data Forms
    chatbot.register_plugin('xep_0060') # PubSub
    chatbot.register_plugin('xep_0199', {'keepalive': True, 'interval': 60, 'timeout': 15}) # XMPP Ping
    if chatbot.connect(('talk.google.com', 5222)):
        logging.info("logged in to talk.google.com")
        chatbot.process(block=False)
    else:
        logging.warning("login to talk.google.com failed")
        sys.exit(0)

    app = QApplication(sys.argv)
    debugUi = DebugGui("Temp sensor disconnected")

    sys.exit(app.exec_())

if __name__ == '__main__':
    thermostat = Thermostat(72.0, 50.0)
    try:
        sensor = BMP085.BMP085()
        start_thermostat(sensor, thermostat)
    except:
        # In case the sensor becomes disconnected
        traceback.print_exc()
        start_debug(thermostat)


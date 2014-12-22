# vim: et:sw=4:ts=4

import logging
import sleekxmpp
import sys
import threading
import time

from enum import Enum
from PyQt4 import QtGui
from subprocess import check_output

import Adafruit_BMP.BMP085 as BMP085

import access_codes

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

class ThermoBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def start(self, event):
        logging.info("chat bot got start event")
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        logging.info("received message %s", msg)
        if msg['type'] in ('chat', 'normal'):
            msg.reply("Thanks for sending\n%(body)s" % msg).send()

Mode = Enum('Mode', 'On Off Thermostat')

class Thermostat():
    def __init__(self, temp, setTemp):
        self._hysteresis = 1.0
        self._stateLock = threading.Lock()

        # each of these need to be observable variables
        # they could be changed by multiple threads
        # (UI / bot / temp poller) and UI needs notification
        # notification when they do
        self._temp = float(temp)
        self._setTemp = float(setTemp)
        self._mode = Mode.Off
        self._heating = False

    def setMode(self, newMode):
        with self._stateLock:
            self._mode = newMode
            if self._mode == Mode.On:
                self.turnOn()
            elif self._mode == Mode.Off:
                self.turnOff()
            elif self._mode == Mode.Thermostat:
                self.checkAction()

    def setSetTemp(self, setTemp):
        with self._stateLock:
            self._setTemp = setTemp
            self.checkAction()

    def setTemp(self, temp):
        with self._stateLock:
            self._temp = float(temp)
            self.checkAction()

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
            logging.info("Turning heat ON")

    def turnOff(self):
        if self._heating:
            self._heating = False
            logging.info("Turning heat OFF")

class ThermostatGui(QtGui.QWidget):
    def __init__(self, thermostat):
        super(ThermostatGui, self).__init__()
        self.thermostat = thermostat
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""color: white;
background-color: black;
border-style: outset;
border-color: grey;
border-width: 5px;
border-radius: 10px;
font: bold 16px;
""")
        btnStyleSheet = """
QPushButton:checked {
  background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #dadbde, stop: 1 #f6f7fa);
  color: black
}"""
        currentTempDisplay = QtGui.QLCDNumber(self)
        currentTempDisplay.display(self.thermostat.getTemp())

        setTempDisplay = QtGui.QLCDNumber(self)
        setTempDisplay.display(self.thermostat.getSetTemp())

        hotterBtn = QtGui.QPushButton('Hotter', self)
        colderBtn = QtGui.QPushButton('Colder', self)

        onBtn = QtGui.QPushButton('On', self)
        onBtn.setCheckable(True)
        onBtn.setStyleSheet(btnStyleSheet)
        offBtn = QtGui.QPushButton('Off', self)
        offBtn.setCheckable(True)
        offBtn.setStyleSheet(btnStyleSheet)
        thermostatBtn = QtGui.QPushButton('Thermostat', self)
        thermostatBtn.setCheckable(True)
        thermostatBtn.setStyleSheet(btnStyleSheet)

        modeGroup = QtGui.QButtonGroup(self)
        modeGroup.addButton(onBtn)
        modeGroup.addButton(offBtn)
        modeGroup.addButton(thermostatBtn)

        hotterBtn.clicked.connect(self.hotterClicked)
        colderBtn.clicked.connect(self.colderClicked)
        onBtn.clicked.connect(self.onClicked)
        offBtn.clicked.connect(self.offClicked)
        thermostatBtn.clicked.connect(self.thermostatClicked)

        ip = check_output(["hostname", "-I"])
        ipLabel = QtGui.QLabel(ip, self)
        ipLabel.setStyleSheet("border-width: 0; border-radius: 0; font: 12px")
        ipLabel.move(0, 0)
        ipLabel.setFixedWidth(320)

        layout = QtGui.QGridLayout()

        layout.addWidget(currentTempDisplay, 0, 0, 2, 3)
        layout.addWidget(setTempDisplay, 0, 3, 2, 2)
        layout.addWidget(hotterBtn, 0, 5, 1, 1)
        layout.addWidget(colderBtn, 1, 5, 1, 1)
        layout.addWidget(onBtn, 2, 0, 1, 2)
        layout.addWidget(offBtn, 2, 2, 1, 2)
        layout.addWidget(thermostatBtn, 2, 4, 1, 2)

        self.setLayout(layout)

        self.currentTempDisplay = currentTempDisplay
        self.onBtn = onBtn
        self.offBtn = offBtn
        self.thermostatBtn = thermostatBtn

        self.showFullScreen()

    def hotterClicked(self):
        self.thermostat.setTemp(min(self.thermostat.getTemp() + 1, 85.0))
        self.currentTempDisplay.display(self.thermostat.getTemp())

    def colderClicked(self):
        self.thermostat.setTemp(max(self.thermostat.getTemp() - 1, 40.0))
        self.currentTempDisplay.display(self.thermostat.getTemp())

    def onClicked(self):
        self.thermostat.setMode(Mode.On)

    def offClicked(self):
        self.thermostat.setMode(Mode.Off)

    def thermostatClicked(self):
        self.thermostat.setMode(Mode.Thermostat)

class TempPollerThread(threading.Thread):
    def __init__(self, sensor, thermostat):
        super(TempPollerThread, self).__init__()
        self._sensor = sensor
        self._thermostat = thermostat

    def run(self):
        while True:
            tC = self._sensor.read_temperature()
            tF = tC * (9.0/5.0) + 32.0
            logging.info("tC: %f, tF: %f", tC, tF)
            self._thermostat.setTemp(tF)
            time.sleep(5)
    
def main():
    logging.basicConfig(filename='log.txt', level=logging.DEBUG)
    logging.info("cabinmeter starting")

    sensor = BMP085.BMP085()
    thermostat = Thermostat(72.0, 78.0)

    tPollerThread = TempPollerThread(sensor, thermostat)
    tPollerThread.start()

    chatbot = ThermoBot(access_codes.jid, access_codes.password)
    chatbot.register_plugin('xep_0030') # Service Discovery
    chatbot.register_plugin('xep_0004') # Data Forms
    chatbot.register_plugin('xep_0060') # PubSub
    chatbot.register_plugin('xep_0199') # XMPP Ping
    if chatbot.connect(('talk.google.com', 5222)):
        logging.info("logged in to talk.google.com")
        chatbot.process(block=False)
    else:
        logging.warning("login to talk.google.com failed")
        sys.exit(0)

    app = QtGui.QApplication(sys.argv)
    theromstatUi = ThermostatGui(thermostat)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


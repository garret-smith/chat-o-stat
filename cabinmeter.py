# vim: et:sw=4:ts=4

import logging
import sleekxmpp
import sys
import threading
import time

from enum import Enum
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from subprocess import check_output

import Adafruit_BMP.BMP085 as BMP085

import access_codes

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

class ThermoBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, thermostat):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.thermostat = thermostat
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def start(self, event):
        logging.info("chat bot got start event")
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        logging.info("received message %s", msg)
        logging.info("roster: %s", self.client_roster)
        if msg['type'] in ('chat', 'normal'):
            if msg['body'] == "?":
                msg.reply("Hi %s, current temp is %.2fF" % (msg['from'], self.thermostat.getTemp())).send()
            else:
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
            n.onMode(self._mode)

    def onSetTemp(self):
        for n in self._toNotify:
            n.onSetTemp(self._setTemp)

    def onTemp(self):
        for n in self._toNotify:
            n.onTemp(self._temp)

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

class ThermostatGui(QWidget):
    def __init__(self, thermostat):
        super(ThermostatGui, self).__init__()
        self.thermostat = thermostat
        self.initUI()
        thermostat.notify(self)

    def initUI(self):
        self.setStyleSheet("""
QWidget {
  background-color: transparent;
  color: white;
  margin: 0px;
}
""")
        btnStyleSheet = """
QPushButton {
  background-color: black;
  color: white;
  border-style: outset;
  border-color: grey;
  border-width: 2px;
  border-radius: 10px;
  padding: 5px;
  font: bold 14pt;
}
QPushButton:checked {
  background-color: grey;
  color: black;
}
"""
        movie = QMovie("fire.gif", QByteArray(), self)
        movieScreen = QLabel(self)
        movieScreen.move(0, 0)
        movieScreen.setFixedWidth(320)
        movieScreen.setFixedHeight(240)
        movieScreen.setMovie(movie)
        movie.setCacheMode(QMovie.CacheAll)
        movie.setSpeed(30)

        currentTempDisplay = QLabel(self)
        currentTempDisplay.setStyleSheet("""
QLabel {
border: -20px;
padding: -20px;
margin: -20px;
font: bold 36pt;
}""")
        currentTempDisplay.setAlignment(Qt.AlignCenter|Qt.AlignHCenter)
        currentTempDisplay.setText("%.1f" % self.thermostat.getTemp())

        setTempDisplay = QLabel(self)
        setTempDisplay.setStyleSheet("""
QLabel {
border: -20px;
padding: -20px;
margin: -20px;
font: bold 22pt;
}""")
        setTempDisplay.setAlignment(Qt.AlignCenter|Qt.AlignHCenter)
        setTempDisplay.setText("%d" % self.thermostat.getSetTemp())

        hotIcon = QIcon("up.png")
        coldIcon = QIcon("down.png")

        hotterBtn = QPushButton('', self)
        hotterBtn.setIcon(hotIcon)
        hotterBtn.setIconSize(QSize(60,30))

        colderBtn = QPushButton('', self)
        colderBtn.setIcon(coldIcon)
        colderBtn.setIconSize(QSize(60,30))

        onBtn = QPushButton('On', self)
        onBtn.setCheckable(True)
        onBtn.setStyleSheet(btnStyleSheet)
        offBtn = QPushButton('Off', self)
        offBtn.setCheckable(True)
        offBtn.setStyleSheet(btnStyleSheet)
        offBtn.setChecked(True)
        thermostatBtn = QPushButton('Thermostat', self)
        thermostatBtn.setCheckable(True)
        thermostatBtn.setStyleSheet(btnStyleSheet)

        modeGroup = QButtonGroup(self)
        modeGroup.addButton(onBtn)
        modeGroup.addButton(offBtn)
        modeGroup.addButton(thermostatBtn)

        hotterBtn.clicked.connect(self.hotterClicked)
        colderBtn.clicked.connect(self.colderClicked)
        onBtn.clicked.connect(self.onClicked)
        offBtn.clicked.connect(self.offClicked)
        thermostatBtn.clicked.connect(self.thermostatClicked)

        ip = check_output(["hostname", "-I"])
        ipLabel = QLabel(ip, self)
        ipLabel.setStyleSheet("border-width: 0; border-radius: 0; font: 12px")
        ipLabel.move(0, 0)
        ipLabel.setFixedWidth(320)

        layout = QGridLayout()
        layout.setMargin(0)

        layout.addWidget(currentTempDisplay, 0, 0, 2, 3)
        layout.addWidget(setTempDisplay, 0, 3, 2, 2)
        layout.addWidget(hotterBtn, 0, 5, 1, 1)
        layout.addWidget(colderBtn, 1, 5, 1, 1)
        layout.addWidget(onBtn, 2, 0, 1, 2)
        layout.addWidget(offBtn, 2, 2, 1, 2)
        layout.addWidget(thermostatBtn, 2, 4, 1, 2)

        self.setLayout(layout)

        self.movie = movie
        self.currentTempDisplay = currentTempDisplay
        self.setTempDisplay = setTempDisplay
        self.onBtn = onBtn
        self.offBtn = offBtn
        self.thermostatBtn = thermostatBtn

        self.showFullScreen()

    def onMode(self, mode):
        if mode == Mode.On:
            self.movie.start()
        elif mode == Mode.Off:
            self.movie.stop()
        elif mode == Mode.Thermostat:
            self.movie.start()

    def onSetTemp(self, setTemp):
        self.setTempDisplay.setText("%d" % setTemp)

    def onTemp(self, temp):
        self.currentTempDisplay.setText("%.1f" % temp)

    def hotterClicked(self):
        self.thermostat.setSetTemp(min(self.thermostat.getSetTemp() + 1, 85.0))
        self.setTempDisplay.setText("%d" % self.thermostat.getSetTemp())

    def colderClicked(self):
        self.thermostat.setSetTemp(max(self.thermostat.getSetTemp() - 1, 40.0))
        self.setTempDisplay.setText("%d" % self.thermostat.getSetTemp())

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
            time.sleep(1)

def main():
    logging.basicConfig(filename='log.txt', level=logging.DEBUG)
    logging.info("cabinmeter starting")

    sensor = BMP085.BMP085()
    thermostat = Thermostat(72.0, 78.0)

    tPollerThread = TempPollerThread(sensor, thermostat)
    tPollerThread.start()

    chatbot = ThermoBot(access_codes.jid, access_codes.password, thermostat)
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

    app = QApplication(sys.argv)
    theromstatUi = ThermostatGui(thermostat)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


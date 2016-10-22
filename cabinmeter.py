# vim: et:sw=4:ts=4

import logging
import logging.config
import sleekxmpp
import sys
import threading
import time
import traceback

from enum import Enum
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from subprocess import check_output,call

import Adafruit_BMP.BMP085 as BMP085

import access_codes

maxT = 80.0
minT = 45.0

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

def safe_checkoutput(args):
    try:
        return check_output(args)
    except CalledProcessError:
        return ""

class DebugBot(sleekxmpp.ClientXMPP):
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
        if msg['type'] in ('chat', 'normal'):
            if msg['from'].user in access_codes.xmpp_auth_accounts:
                mode = self.thermostat.getMode()
                body = msg['body'].lower()
                if body == "?":
                    msg.reply("[Sensor disconnected] Mode is %s" % mode.name).send()
                if body == "uptime":
                    msg.reply("[Sensor disconnected] %s" % safe_checkoutput(["uptime"])).send()
                if body == "log":
                    msg.reply("[Sensor disconnected] %s" % safe_checkoutput(["cat", "/tmp/cabin.stdout"])).send()
                if body == "reboot":
                    call(["sudo", "shutdown", "-r", "now"])
                if body == "restart":
                    call(["killall", "python"])
                elif body == 'on':
                    self.thermostat.setMode(Mode.On)
                    msg.reply("[Sensor disconnected] Heat is ON.").send()
                elif body == 'off':
                    self.thermostat.setMode(Mode.Off)
                    msg.reply("[Sensor disconnected] Heat is OFF.").send()
                else:
                    msg.reply("[Sensor disconnected] I don't know what '%s' means." % body).send()
            else:
                    msg.reply("Not sure I can trust you, %s." % msg['from'].user).send()


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
        if msg['type'] in ('chat', 'normal'):
            if msg['from'].user in access_codes.xmpp_auth_accounts:
                setTemp = self.thermostat.getSetTemp()
                temp = self.thermostat.getTemp()
                mode = self.thermostat.getMode()
                body = msg['body'].lower()
                if body == "?":
                    if mode == Mode.On:
                        msg.reply("Heat is ON.  Current temp is %.1f" % temp).send()
                    elif mode == Mode.Off:
                        msg.reply("Heat is OFF.  Current temp is %.1f" % temp).send()
                    elif mode == Mode.Thermostat:
                        msg.reply("Thermostat is set to %.0f.  Current temp is %.1f" % (setTemp, temp)).send()
                    else:
                        msg.reply("I know you're smarter than this").send()
                elif body == 'on':
                    self.thermostat.setMode(Mode.On)
                    msg.reply("Heat is ON.  Current temp is %.1f" % temp).send()
                elif body == 'off':
                    self.thermostat.setMode(Mode.Off)
                    msg.reply("Heat is OFF.  Current temp is %.1f" % temp).send()
                elif body.startswith('set '):
                    try:
                        newSetTemp = float(body[4:])
                        if newSetTemp < minT:
                            msg.reply("%.0f seems awful cold" % newSetTemp).send()
                        elif newSetTemp > maxT:
                            msg.reply("%.0f seems awful hot" % newSetTemp).send()
                        else:
                            self.thermostat.setSetTemp(newSetTemp)
                            self.thermostat.setMode(Mode.Thermostat)
                            msg.reply("Thermostat is set to %.0f.  Current temp is %.1f" % (newSetTemp, temp)).send()
                    except Exception as e:
                        msg.reply("I can't set the thermostat to '%s'" % body[4:]).send()
                else:
                    msg.reply("I don't know what '%s' means." % body).send()
            else:
                    msg.reply("Not sure I can trust you, %s." % msg['from'].user).send()

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
            n.onMode(self._mode)

    def onSetTemp(self):
        for n in self._toNotify:
            n.onSetTemp(self._setTemp)

    def onTemp(self):
        for n in self._toNotify:
            n.onTemp(self._temp)

    def onHeating(self):
        for n in self._toNotify:
            n.onHeating(self._heating)

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

class DebugGui(QWidget):
    def __init__(self, message):
        super(DebugGui, self).__init__()
        self.message = message
        self.initUI()

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

        onBtn = QPushButton('On', self)
        onBtn.setCheckable(True)
        onBtn.setStyleSheet(btnStyleSheet)
        offBtn = QPushButton('Off', self)
        offBtn.setCheckable(True)
        offBtn.setStyleSheet(btnStyleSheet)

        modeGroup = QButtonGroup(self)
        modeGroup.addButton(onBtn)
        modeGroup.addButton(offBtn)

        onBtn.clicked.connect(self.onClicked)
        offBtn.clicked.connect(self.offClicked)

        ip = check_output(["hostname", "-I"])
        ipLabel = QLabel(ip, self)
        ipLabel.setStyleSheet("border-width: 0; border-radius: 0; font: 12px")
        ipLabel.move(0, 0)
        ipLabel.setFixedWidth(320)

        messageLabel = QLabel(self.message, self)
        messageLabel.move(0, 10)
        messageLabel.setFixedWidth(320)

        layout = QGridLayout(self)
        layout.setMargin(0)

        layout.addWidget(onBtn, 2, 0, 1, 2)
        layout.addWidget(offBtn, 2, 2, 1, 2)

        self.setLayout(layout)

        self.onBtn = onBtn
        self.offBtn = offBtn

        self.showFullScreen()

    def onMode(self, mode):
        if mode == Mode.On:
            self.onBtn.setChecked(True)
        elif mode == Mode.Off:
            self.offBtn.setChecked(True)

    def onClicked(self):
        self.thermostat.setMode(Mode.On)

    def offClicked(self):
        self.thermostat.setMode(Mode.Off)

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
        firemovie = QMovie("fire.gif", QByteArray(), self)
        firemovie.setCacheMode(QMovie.CacheAll)
        firemovie.setSpeed(40)
        firemovie.start()

        bluefiremovie = QMovie("bluefire.gif", QByteArray(), self)
        bluefiremovie.setCacheMode(QMovie.CacheAll)
        bluefiremovie.setSpeed(40)
        bluefiremovie.start()

        movieScreen = QLabel(self)
        movieScreen.move(0, 0)
        movieScreen.setFixedWidth(320)
        movieScreen.setFixedHeight(240)
        movieScreen.setMovie(bluefiremovie)

        currentTempDisplay = QLabel(self)
        currentTempDisplay.setStyleSheet("""
QLabel {
border: -20px;
padding: -20px;
padding-right: -40px;
margin: -20px;
font: bold 48pt;
}""")
        currentTempDisplay.setAlignment(Qt.AlignCenter|Qt.AlignHCenter)
        currentTempDisplay.setText("%.1f" % self.thermostat.getTemp())

        setTempDisplay = QLabel(self)
        setTempDisplay.setStyleSheet("""
QLabel {
border: -20px;
padding: -20px;
padding-right: -40px;
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
        thermostatBtn = QPushButton('Thermostat', self)
        thermostatBtn.setCheckable(True)
        thermostatBtn.setStyleSheet(btnStyleSheet)
        thermostatBtn.setChecked(True)

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

        layout = QGridLayout(self)
        layout.setMargin(0)

        layout.addWidget(currentTempDisplay, 0, 0, 2, 4)
        layout.addWidget(setTempDisplay, 0, 4, 2, 1)
        layout.addWidget(hotterBtn, 0, 5, 1, 1)
        layout.addWidget(colderBtn, 1, 5, 1, 1)
        layout.addWidget(onBtn, 2, 0, 1, 2)
        layout.addWidget(offBtn, 2, 2, 1, 2)
        layout.addWidget(thermostatBtn, 2, 4, 1, 2)

        self.setLayout(layout)

        self.bluefiremovie = bluefiremovie
        self.firemovie = firemovie
        self.movieScreen = movieScreen
        self.currentTempDisplay = currentTempDisplay
        self.setTempDisplay = setTempDisplay
        self.onBtn = onBtn
        self.offBtn = offBtn
        self.thermostatBtn = thermostatBtn

        self.showFullScreen()

    def onMode(self, mode):
        if mode == Mode.On:
            self.onBtn.setChecked(True)
        elif mode == Mode.Off:
            self.offBtn.setChecked(True)
        elif mode == Mode.Thermostat:
            self.thermostatBtn.setChecked(True)

    def onSetTemp(self, setTemp):
        self.setTempDisplay.setText("%d" % setTemp)

    def onTemp(self, temp):
        self.currentTempDisplay.setText("%.1f" % temp)

    def onHeating(self, heating):
        if heating:
            self.movieScreen.setMovie(self.firemovie)
        else:
            self.movieScreen.setMovie(self.bluefiremovie)

    def hotterClicked(self):
        self.thermostat.setSetTemp(min(self.thermostat.getSetTemp() + 1, maxT))
        self.setTempDisplay.setText("%d" % self.thermostat.getSetTemp())

    def colderClicked(self):
        self.thermostat.setSetTemp(max(self.thermostat.getSetTemp() - 1, minT))
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


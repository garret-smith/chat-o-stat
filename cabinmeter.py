
import sys
from PyQt4 import QtGui

from subprocess import check_output
from enum import Enum

from twython import Twython

import access_codes

def tweet():
    api = Twython(access_codes.CONSUMER_KEY,
		  access_codes.CONSUMER_SECRET,
		  access_codes.ACCESS_KEY,
		  access_codes.ACCESS_SECRET)
    api.update_status(status="Twython test tweet!")

Mode = Enum('Mode', 'On Off Thermostat')
Relay = Enum('Relay', 'Open Closed')

class Thermostat():
    """
    Need some kind of delay on user actions, so that user can click something,
    like "mode", and the action won't take effect for a second or so.
    ie, give the user time to continue cycling the mode to the desired mode.
    """

    def __init__(self, temp, setTemp):
        self._hysteresis = 1.0

        self._temp = float(temp)
        self._setTemp = float(setTemp)
        self._mode = Mode.Off
        self._heating = False
        self._relay = Relay.Open

    def setMode(self, newMode):
        self._mode = newMode
        if self._mode == Mode.On:
            self.turnOn()
        elif self._mode == Mode.Off:
            self.turnOff()
        elif self._mode == Mode.Thermostat:
            self.checkAction()

    def setSetTemp(self, setTemp):
        self._setTemp = setTemp
        self.checkAction()

    def setTemp(self, temp):
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
            self._relay = Relay.Closed
            self._heating = True
            print "Turning on"

    def turnOff(self):
        if self._heating:
            self._relay = Relay.Open
            self._heating = False
            print "Turning off"

class ThermostatGui(QtGui.QWidget):
    def __init__(self):
        super(ThermostatGui, self).__init__()
        self.thermostat = Thermostat(72.0, 78.0)
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

def main():
    app = QtGui.QApplication(sys.argv)
    theromstat = ThermostatGui()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


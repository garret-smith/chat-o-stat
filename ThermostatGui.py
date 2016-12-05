
import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from subprocess import check_output

from Thermostat import Mode
from config import minT,maxT

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



import logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from subprocess import check_output

from Thermostat import Mode

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


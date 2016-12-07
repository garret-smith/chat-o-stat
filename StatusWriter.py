
import logging
import threading

from decimal import Decimal
from datetime import datetime

import boto3

from Thermostat import Mode
import config

class StatusWriter():
    def __init__(self, thermostat):
        self.thermostat = thermostat
        thermostat.notify(self)
        self.event_write_timer = None
        dynamo = boto3.resource('dynamodb')
        self.status_table = dynamo.Table(config.status_table_name)
        t = threading.Timer(config.status_table_write_time, self.rescheduling_write)
        t.start()

    def rescheduling_write(self):
        logging.debug("running scheduled write")
        self.write()
        t = threading.Timer(config.status_table_write_time, self.rescheduling_write)
        t.start()

    def event_write(self):
        logging.debug("running event write")
        self.event_write_timer = None
        self.write()

    def write(self):
        try:
            mode = self.thermostat.getMode()
            setTemp = self.thermostat.getSetTemp()
            temp = self.thermostat.getTemp()
            now = datetime.now()
            day = now.strftime('%Y-%m-%d')
            time = now.strftime('%H:%M:%S')
            status = {
                    'day': day,
                    'time': time,
                    'mode': str(mode),
                    'setTemp': Decimal(str(setTemp)),
                    'temp': Decimal(str(temp))
                    }
            self.status_table.put_item(Item = status)
        except:
            logging.error("status write failed", exc_info=True)

    def onMode(self, mode):
        if self.event_write_timer is not None:
            self.event_write_timer.cancel()
        self.event_write_timer = threading.Timer(5, self.event_write)
        self.event_write_timer.start()

    def onSetTemp(self, setTemp):
        if self.event_write_timer is not None:
            self.event_write_timer.cancel()
        self.event_write_timer = threading.Timer(5, self.event_write)
        self.event_write_timer.start()

    def onTemp(self, temp):
        pass

    def onHeating(self, heating):
        pass


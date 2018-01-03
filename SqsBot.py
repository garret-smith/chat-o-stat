
import json
import logging
import threading
import time

import boto3

from Thermostat import Mode
import config

class SqsBot(threading.Thread):
    def __init__(self, thermostat):
        threading.Thread.__init__(self)
        self.thermostat = thermostat

    def run(self):
        session = boto3.session.Session()
        sqs = session.resource('sqs')
        inbound_q = sqs.get_queue_by_name(QueueName=config.in_q_name)
        while True:
            try:
                logging.debug("polling message q")
                for message in inbound_q.receive_messages():
                    logging.debug("processing message: %s", message)
                    self.process_message(message.body)
                    message.delete()
            except:
                logging.exception("queue polling / processing failed")
            finally:
                time.sleep(config.q_poll_time)


    def process_message(self, body):
        msg = json.loads(body)
        if msg.has_key('setTemp'):
            setTemp = max(min(float(msg['setTemp']), config.maxT), config.minT)
            self.thermostat.setSetTemp(setTemp)
        mode = msg['mode'].lower()
        if mode == 'on':
            self.thermostat.setMode(Mode.On)
        elif mode == 'off':
            self.thermostat.setMode(Mode.Off)
        elif mode == 'thermostat':
            self.thermostat.setMode(Mode.Thermostat)



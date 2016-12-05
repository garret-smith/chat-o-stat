
import logging
import sleekxmpp

from subprocess import check_output,call

import access_codes

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



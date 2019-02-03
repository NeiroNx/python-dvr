#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import json
from time import sleep
import hashlib
import threading
from socket import *
from datetime import *


class DVRIPCam(object):
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    CODES = {
        100: "OK",
        101: "Unknown error",
        102: "Unsupported version",
        103: "Request not permitted",
        104: "User already logged in",
        105: "User is not logged in",
        106: "Username or password is incorrect",
        107: "User does not have necessary permissions",
        203: "Password is incorrect",
        515: "Upgrade successful"
    }
    QCODES = {
        "AlarmInfo": 1504,
        "AlarmSet": 1500,
        "KeepAlive": 1006,
        "ChannelTitle": 1046,
        "OPTimeQuery": 1452,
        "OPTimeSetting": 1450,
        "OPMailTest": 1636,
        #{ "Name" : "OPMailTest", "OPMailTest" : { "Enable" : true, "MailServer" : { "Address" : "0x00000000", "Anonymity" : false, "Name" : "Your SMTP Server", "Password" : "", "Port" : 25, "UserName" : "" }, "Recievers" : [ "", "none", "none", "none", "none" ], "Schedule" : [ "0 00:00:00-24:00:00", "0 00:00:00-24:00:00" ], "SendAddr" : "", "Title" : "Alarm Message", "UseSSL" : false }, "SessionID" : "0x1" }
        "OPMachine": 1450,
        "OPMonitor": 1413,
        "OPTalk": 1434,
        "OPPTZControl": 1400,
        "OPNetKeyboard": 1550,
        "SystemFunction": 1360,
        "EncodeCapability": 1360
    }
    KEY_CODES = {
        "M": "Menu",
        "I": "Info",
        "E": "Esc",
        "F": "Func",
        "S": "Shift",
        "L": "Left",
        "U": "Up",
        "R": "Right",
        "D": "Down"
    }
    OK_CODES = [100, 515]

    def __init__(self, ip, user="admin", password="", port=34567):
        self.ip = ip
        self.user = user
        self.password = password
        self.port = port
        self.socket = None
        self.packet_count = 0
        self.session = 0
        self.alive_time = 200
        self.alive = None
        self.alarm = None
        self.alarm_func = None
        self.busy = threading.Condition()

    def connect(self):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(1)

    def close(self):
        self.alive.cancel()
        self.socket.close()
        self.socket = None

    def send(self, msg, data):
        if self.socket == None:
            return {"Ret": 101}
        # self.busy.wait()
        self.busy.acquire()
        if hasattr(data, '__iter__'):
            data = json.dumps(data, ensure_ascii=False).encode('utf8')

        self.socket.send(struct.pack('BB2xII2xHI', 255, 0, self.session,
                                     self.packet_count, msg, len(data)+2)+data+"\x0a\x00".encode('utf-8'))
        reply = {"Ret": 101}
        try:
            head, version, self.session, sequence_number, msgid, len_data = struct.unpack(
                'BB2xII2xHI', self.socket.recv(20))
            sleep(.05)  # Just for recive whole packet
            reply = self.socket.recv(len_data)
            self.packet_count += 1
            reply = json.loads(reply[:-2], encoding="utf-8")
            print(reply)
        except Exception as e:
            print("Exception : ", e)
        finally:
            self.busy.release()
        return reply

    def sofia_hash(self, password):
        s = ""
        password = password.encode("utf-8")
        md5 = hashlib.md5(password).digest()
        for n in range(8):
            c = (md5[2*n]+md5[2*n+1]) % 62
            if c > 9:
                if c > 35:
                    c += 61
                else:
                    c += 55
            else:
                c += 48
            s += chr(c)
        return s

    def login(self):
        if self.socket == None:
            self.connect()
        data = self.send(1000, {"EncryptType": "MD5", "LoginType": "DVRIP-Web",
                                "PassWord": self.sofia_hash(self.password), "UserName": self.user})
        self.session = int(data["SessionID"], 16)
        self.alive_time = data["AliveInterval"]
        self.keep_alive()
        return data["Ret"] in self.OK_CODES

    def channel_title(self, title):
        return self.send(self.QCODES["ChannelTitle"], {'ChannelTitle': [
            title], "Name": "ChannelTitle", "SessionID": "0x%08X" % self.session})

    def reboot(self):
        self.send_command(self.QCODES["OPMachine"],
                          "OPMachine", {"Action": "Reboot"})
        self.close()

    def pretty_print(self, data):
        print(json.dumps(data, indent=4, sort_keys=True))

    def setAlarm(self, func):
        self.alarm_func = func

    def clearAlarm(self):
        self.alarm_func = None

    def alarmStart(self):
        self.alarm = threading.Thread(
            name="DVRAlarm%08X" % self.session, target=self.alarm_thread, args=[self.busy])
        self.alarm.start()
        return self.get(self.QCODES["AlarmSet"], "")

    def alarm_thread(self, event):
        while True:
            event.acquire()
            try:
                head, version, session, sequence_number, msgid, len_data = struct.unpack(
                    'BB2xII2xHI', self.socket.recv(20))
                sleep(.1)  # Just for recive whole packet
                reply = self.socket.recv(len_data)
                self.packet_count += 1
                reply = json.loads(reply[:-2], encoding="utf8")
                if msgid == self.QCODES["AlarmInfo"] and self.session == session:
                    if self.alarm_func != None:
                        self.alarm_func(reply[reply['Name']], sequence_number)
            except:
                pass
            finally:
                event.release()
            if self.socket == None:
                break

    def keep_alive(self):
        self.send(self.QCODES["KeepAlive"], {
            "Name": "KeepAlive",
                    "SessionID": "0x%08X" % self.session})
        self.alive = threading.Timer(self.alive_time, self.keep_alive)
        self.alive.start()

    def keyDown(self, key):
        return self.send_command(self.QCODES["OPNetKeyboard"],
                                 "OPNetKeyboard",
                                 {"Status": "KeyDown", "Value": key})

    def keyUp(self, key):
        return self.send_command(self.QCODES["OPNetKeyboard"],
                                 "OPNetKeyboard",
                                 {"Status": "KeyUp", "Value": key})

    def keyPress(self, key):
        self.keyDown(key)
        sleep(.3)
        self.keyUp(key)

    def keyScript(self, keys):
        for k in keys:
            if k != " " and k.upper() in self.KEY_CODES:
                self.keyPress(self.KEY_CODES[k.upper()])
            else:
                sleep(1)

    def ptz(self, cmd, ch=0):
        ptz_param = {
            "AUX":
                {"Number": 0,
                 "Status": "On"},
            "Channel": ch,
            "MenuOpts": "Enter",
            "POINT": {"bottom": 0, "left": 0, "right": 0, "top": 0},
            "Pattern": "SetBegin", "Preset": -1, "Step": 5, "Tour": 0}
        return self.send_command(self.QCODES["OPPTZControl"], "OPPTZControl",
                                 {"Command": cmd, "Parameter": ptz_param})

    def move_it(self, cmd, ch=0, status='On', preset=0):
        """Moves the camera (or at least tries to)

        Arguments:
            cmd {command} -- Direction. Example: DirectionUp. Valid options are: Up|Down|Left|Right

        Keyword Arguments:
            ch {int} -- Channel (default: {0})

        Returns:
            str -- Reply message
        """

        Parameter = {
            "AUX":
                {"Number": 0, "Status": status},
            "Channel": ch,
            "MenuOpts": "Enter",
            "Pattern": "Start",
            "Preset": preset,
            "Step": 30,
            "Tour": 0
        }
        return self.send_command(self.QCODES["OPPTZControl"], "OPPTZControl",
                                 {"Command": cmd, "Parameter": Parameter})

    def stop_it(self, ch=0):
        """Stops the Camera motion. (This is probably not the best way, but it works).
        Stopping is done by setting the preset value to -1 in a valid command message.

        Keyword Arguments:
                ch {int} -- Camera channel (default: {0})

        Returns:
                str -- Reply JSON
        """

        return self.move_it("DirectionUp", ch=ch, preset=-1)

    def set_info(self, command, data):
        """Sets info

        Arguments:
            command {} -- 
            data {} -- 
        """

        return self.send_command(1040, command, data)

    def send_command(self, code, command, data):
        """Send command to the camera

        Arguments:
            code  
            command 
            data 
        """
        return self.send(code, {"Name": str(command),
                                "SessionID": "0x%08X" % self.session,
                                str(command): data})

    def get_info(self, code, command):
        return self.get(code, command)

    def get(self, code, command):
        data = self.send(code, {"Name": str(command),
                                "SessionID": "0x%08X" % self.session})
        if data["Ret"] in self.OK_CODES and str(command) in data:
            return data[str(command)]
        else:
            return data

    def get_time(self):
        return datetime.strptime(self.get(self.QCODES["OPTimeQuery"], "OPTimeQuery"), self.DATE_FORMAT)

    def set_time(self, time=None):
        if time == None:
            time = datetime.now()
        return self.send_command(self.QCODES["OPTimeSetting"], "OPTimeSetting", time.strftime(self.DATE_FORMAT))

    def get_system_info(self):
        data = self.get(1042, "General")
        self.pretty_print(data)

    def get_encode_capabilities(self):
        data = self.get(self.QCODES["EncodeCapability"], "EncodeCapability")
        self.pretty_print(data)

    def get_system_capabilities(self):
        data = self.get(self.QCODES["SystemFunction"], "SystemFunction")
        self.pretty_print(data)

    def get_camera_info(self, default=False):
        """Request data for 'Camera' from  the target DVRIP device."""
        if default:
            code = 1044
        else:
            code = 1042
        data = self.get_info(code, "Camera")
        return data

    def get_encode_info(self, default=False):
        """Request data for 'Simplify.Encode' from the target DVRIP device.

                Arguments:
                default -- returns the default values for the type if True

        """

        if default:
            code = 1044
        else:
            code = 1042

        data = self.get_info(code, "Simplify.Encode")
        self.pretty_print(data)


if __name__ == "__main__":
	#Just a simple test run to check communciation
    def pretty_print(data):
        print(json.dumps(data, indent=4, sort_keys=True))

	#TODO : Check ip and credentials 
    cam = DVRIPCam("<INSERT IP HERE>", "admin", "")
    cam.login()
    time = cam.get_time()
    print("CAM Time:{0}".format(time))
    # Reboot test
    print("Update time...")

    data = cam.get_camera_info()
    pretty_print(data)
    encode_info = cam.get_encode_info()
    pretty_print(encode_info)
    cam.get_system_capabilities()
    cam.close()
    print("Cam closed..")

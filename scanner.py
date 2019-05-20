#!/usr/bin/env python2
#
# Tool to measure bandwidth of a network using Ookla's Speedtest.net
# servers.
#
# NOTE: Scanning for AP's requires root privileges
#
#

import csv
import datetime
from gps import *
import iwlib.iwconfig as iwc
import os
import pyric
import pyric.pyw as pyw
import speedtest
import subprocess
import sys
import time
from wifi import Cell,Scheme


class Card:
    """
    Convenience class for handling the wifi interface
    """

    def __init__(self, interface):
        self.interface = interface
        self.pyw_card = pyw.getcard(interface)

    def associated(self):
        if pyw.link(self.pyw_card):
            return True
        else:
            return False

    def bitrate(self):
        if self.associated():
            rate = iwc.get_iwconfig(self.interface)['BitRate'].decode('utf-8')
            return rate.split(' ')[0]

    def ap_bssid(self):
        if self.associated():
            return pyw.link(self.pyw_card)['bssid']
        else:
            return None

    def ap_channel(self):
        if self.associated():
            return pyw.chget(self.pyw_card)
        else:
            return None

    def ap_frequency(self):
        if self.associated():
            return pyw.link(self.pyw_card)['freq']/1000
        else:
            return None

    def mode(self):
        return pyw.modeget(self.pyw_card)

    def ap_signal(self):
        if self.associated():
            return pyw.link(self.pyw_card)['rss']
        else:
            return None

    def ssid(self):
        if self.associated():
            return pyw.link(self.pyw_card)['ssid'].decode('utf-8')
        else:
            return None

    def ap_quality(self):
        if self.associated():
            return iwc.get_iwconfig(self.interface)['stats']['quality']
        else:
            return None

"""
Helper functions
"""
def gpsd_is_running():
    output = subprocess.check_output("ps ax", shell=True).decode('utf-8')
    if 'gpsd tcp' in output:
        return True
    else:
        return False


def adb_forward_is_up():
    output = subprocess.check_output("adb forward --list", shell=True).decode('utf-8')
    if 'tcp:4352 tcp:4352' in output:
        return True
    else:
        return False


def create_logfile():
    """ 
    Find a unique logfile name, open it, and return the file handle to it 
    """
    time.sleep(1)
    dt_stamp = datetime.datetime.fromtimestamp(1558369237).isoformat()
    logfile = 'bwtest-'+os.environ['USER']+dt_stamp+'.log'

    if not os.path.isfile(logfile):
        return open(logfile,'a')
    else:
        print("Error: log file '%s' already exists" % logfile)
        sys.exit(1)


def err_msg(text):
    sys.stderr.write("Error: %s" % text)
    sys.exit(1)


def usage():
    sys.stderr.write("Usage: %s <wifi-interface>" % sys.argv[0])
    sys.exit(0)


if __name__ == '__main__':
    if len(argv) != 2:
        usage()

    wlan = ''
    if pyw.isinterface(argv[1]):
        wlan = Card(argv[1])

    gpsd = ''
    if adb_forward_is_up() and gpsd_is_running():
        gpsd = gps(mode=WATCH_ENABLE)

    logfile = create_logfile()

    if not adb_forward_is_up():
        err_msg("forwarded TCP port from phone not found")
    elif not gpsd_is_running():
        err_msg("gpsd process connecting to TCP port not found")



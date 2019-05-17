#!/usr/bin/env python3
#
# Tool to measure bandwidth of a network using Ookla's Speedtest.net
# servers.
#
# NOTE: Scanning for AP's reqiures root privileges
#
#

from gps import *
import iwlib.iwconfig as iwc
import os
import pyric
import pyric.pyw as pyw
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



if __name__ == '__main__':
    # start it up
    print('moo')

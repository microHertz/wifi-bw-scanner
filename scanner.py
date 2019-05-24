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
from io import StringIO
import iwlib.iwconfig as iwc
import os
import pyric
import pyric.pyw as pyw
import speedtest
import subprocess
import sys
import time
from wifi import Cell,Scheme


class GpsdLockFailure(Exception):
    """
    Basic exception raised if unable to acquire a TPV message from GPSD
    """


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
            return float(rate.split(' ')[0])
        else:
            return 0.0

    def ap_bssid(self):
        if self.associated():
            return pyw.link(self.pyw_card)['bssid'].upper()
        else:
            return ''

    def ap_channel(self):
        if self.associated():
            return pyw.chget(self.pyw_card)
        else:
            return 0

    def ap_frequency(self):
        if self.associated():
            return pyw.link(self.pyw_card)['freq']/1000.0
        else:
            return 0.0

    def mode(self):
        return pyw.modeget(self.pyw_card)

    def ap_rssi(self):
        if self.associated():
            return pyw.link(self.pyw_card)['rss']
        else:
            return 0

    def ssid(self):
        if self.associated():
            return pyw.link(self.pyw_card)['ssid'].decode('utf-8')
        else:
            return ''

    def ap_quality(self):
        if self.associated():
            return iwc.get_iwconfig(self.interface)['stats']['quality']
        else:
            return 0

    def get_wlan_dict(self):
        return { 
            'associated': self.associated(),
            'interface': self.interface,
            'bitrate': self.bitrate(),
            'ssid': self.ssid(),
            'bssid': self.ap_bssid(),
            'channel': self.ap_channel(),
            'rssi': self.ap_rssi(),
            'quality': self.ap_quality(),
            'frequency': self.ap_frequency(),
            'mode': self.mode(),
        }


class ScanLog(object):
    """
    Class to encapsulate scanning and logging functions
    """
    better_ap_columns_dict = {
        'bssid': '',
        'rssi': 0,
        'quality': 0,
        'frequency': 0.0,
    }

    log_columns_dict = {
        'time': 0,
        'ssid': '',
        'bssid': '',
        'rssi': 0,
        'quality': 0,
        'frequency': 0.0,
        'lat': 0.0,
        'lon': 0.0,
        'download': 0.0,
        'upload': 0.0,
        'test-server-city': '',
        'test-server-url': '',
        'test-server-latency': 0.0,
        'better-ap': better_ap_columns_dict
    }

    def __init__(self, gpsd=None, wlan=None, test_runs=3):
        self.gpsd = gpsd
        self.logfile = self.new_logfile()
        self.spdtest = speedtest.Speedtest()
        self.spdtest.get_best_server()
        self.test_runs = test_runs
        self.wlan = wlan

        self.curr_log = {}
        self.curr_better_ap = {}

    def new_logfile(self):
        """ 
        Find a unique logfile name, open it, and return the file handle to it 
        """
        time.sleep(1)
        dt_stamp = self.get_timestamp()
        logfile = 'bwtest-'+os.environ['USER']+dt_stamp+'.log'

        if not os.path.isfile(logfile):
            return open(logfile,'a')
        else:
            print("Error: log file '%s' already exists" % logfile)
            sys.exit(1)

    def close_logfile(self):
        self.logfile.flush()
        self.logfile.close()

    def flush_logfile(self):
        self.logfile.flush()

    def get_log_pretest(self):
        pass

    def run_tests(self):
        self.curr_log = self.log_columns_dict.copy()
        self.curr_log['time'] = self.get_timestamp()
        self.curr_log['ssid'] = self.wlan.ssid()
        self.curr_log['bssid'] = self.wlan.ap_bssid()
        self.curr_log['rssi'] = self.wlan.ap_rssi()
        self.curr_log['quality'] = self.wlan.ap_quality()
        self.curr_log['frequency'] = self.wlan.ap_frequency()
        self.curr_log['test-server-city'] = self.spdtest._best['name']
        self.curr_log['test-server-url'] = self.spdtest._best['url']
        self.curr_log['test-server-latency'] = self.spdtest._best['latency']
        self.curr_log['lat'], self.curr_log['lon'] = get_gps_coords(self.gpsd)
        self.curr_log['download'] = self.run_download_test()
        self.curr_log['upload'] = self.run_upload_test()
        wdict = self.wlan.get_wlan_dict()
        self.curr_log['better-ap'] = find_best_ap(wdict)

    def run_download_test(self):
        """
        Run download speed test an arbitrary amount and find sample mean
        """
        dl_rate = 0.0
        for run in range(self.test_runs):
            dl_rate += self.spdtest.download()
            time.sleep(1)

        return dl_rate / self.test_runs

    def run_upload_test(self):
        """
        Run upload speed test an arbitrary amount and find sample mean
        """
        ul_rate = 0.0
        for run in range(self.test_runs):
            ul_rate += self.spdtest.upload()
            time.sleep(1)

        return ul_rate / self.test_runs

    @classmethod
    def csv_header(cls):
        """
        Return header row of CSV columns
        """
        return cls.log_columns_dict.keys()

    @classmethod
    def csv_header_better_ap(cls):
        """
        Return header row of CSV volumns for better AP
        """
        return cls.better_ap_columns_dict.keys()

    @staticmethod
    def get_timestamp():
        """
        Time stamp in ISO format with seconds represented as whole numbers
        """
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())


"""
Helper functions
"""
def gpsd_is_running():
    output = subprocess.check_output("ps ax", shell=True).decode('utf-8')
    if 'gpsd tcp' in output:
        return True
    else:
        return False


def get_gps_coords(gpsd):
    """
    Obtain to GPS coordinates from gpsd. If unable to retrieve a
    Time, Position, Velocity (TPV) (i.e. no GPS lock) message after a certain
    number of attempts, raise an exception.
    """
    try:
        for attempts in range(0,15):
            report = gpsd.next()
            if report['class'] == 'TPV':
                lat = getattr(report,'lat',0.0)
                lon = getattr(report,'lon',0.0)
                break
        else:
            # Exhausted attempts, raise exception
            raise GpsdLockFailure('Exhausted attempts to grab GPS lock')

    except (KeyboardInterrupt, GpsdLockFailure):
        # gpsd interrupted, return sentinel values
        lat, lon = 0, 0

    return lat, lon


def adb_forward_is_up():
    output = subprocess.check_output("adb forward --list", shell=True).decode('utf-8')
    if 'tcp:4352 tcp:4352' in output:
        return True
    else:
        return False


def find_best_ap(wlan_dict):
    """
    Given current associated BSSID and signal at time of speed test, search for
    another AP with better characteristics.
    """
    cells = Cell.where(wlan_dict['interface'], find_eduroam)
    best_cell = None
    cell_dict = ScanLog.better_ap_columns_dict.copy()
    for idx,cell in enumerate(cells):
        if wlan_dict['bssid'] != cell.address:
            if same_band(wlan_dict['frequency'],float(cell.frequency.split(' ')[0])) \
            and wlan_dict['rssi'] < cell.signal:
                best_cell = cell
    else:
        if best_cell:
            cell_dict['bssid'] = best_cell.address
            cell_dict['signal'] = best_cell.signal
            cell_dict['quality'] = int(best_cell.quality.split('/')[0])
            cell_dict['frequency'] = float(cell.frequency.split(' ')[0])

    return cell_dict


def find_eduroam(cell):
    """
    This function is meant to be be used with wifi.Cell.where(), which has
    a call to filter() to sort through results.
    """
    if 'eduroam' == cell.ssid:
        return True
    return False


def same_band(freq1, freq2):
    """
    Test whether two given frequencies are in the same band.
    """
    return freq1 // int(freq2) == 1



def err_msg(text):
    sys.stderr.write("Error: %s\n" % text)
    sys.exit(1)


def usage():
    sys.stderr.write("Usage: %s <wifi-interface>\n" % sys.argv[0])
    sys.exit(0)


def scan(speedtest, wlan, gpsd, logfile):
    pass

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()

    wlan = ''
    if pyw.isinterface(sys.argv[1]):
        wlan = Card(sys.argv[1])
    else:
        err_msg("invalid wifi interface " + sys.argv[1])

    if not wlan.associated():
        err_msg("wifi card not associated with AP")

    if not adb_forward_is_up():
        err_msg("forwarded TCP port from phone not found")
    elif not gpsd_is_running():
        err_msg("gpsd process connecting to TCP port not found")

    gpsd = gps(mode=WATCH_ENABLE)


    spdtest = speedtest.Speedtest()

    scan(spdtest, wlan, gpsd, logfile)

    # Exiting



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
from getch import getch
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


class GpsdFailure(Exception):
    """ Based GPSD exception """

class GpsdLockFailure(GpsdFailure):
    """ Unable to acquire a TPV message from GPSD """

class GpsdProcessNotFound(GpsdFailure):
    """ GPSD process not found or incorrect arguments """

class GpsdAdbBridgeError(GpsdFailure):
    """ ADB port forward from phone is missing """


class Card(object):
    """
    Convenience class for handling the wifi interface
    """

    def __init__(self, interface):
        self.interface = interface
        self.pyw_card = pyw.getcard(self.interface)

    def __str__(self):
        output = 'SSID: {}\tBSSID: {}\tAssociated: {}\n\n'.format(self.ssid(), \
                self.ap_bssid(), self.associated())
        output += 'RSSI: {}\tQuality: {}/70\tFrequency: {} GHz\n\n'.format(self.ap_rssi(), \
                self.ap_quality(), self.ap_frequency())
        output += 'Channel: {}\tBitrate: {} Mbps\n'.format(self.ap_channel(), self.bitrate())
        return output

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
    bap_columns_dict = {
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
        'bitrate': 0.0,
        'lat': 0.0,
        'lon': 0.0,
        'download': 0.0,
        'upload': 0.0,
        'test-server-city': '',
        'test-server-url': '',
        'test-server-latency': 0.0,
        'bap-bssid': '',
        'bap-rssi': 0,
        'bap-quality': 0,
        'bap-frequency': 0.0
    }

    columns_order = ['time','ssid','bssid','rssi','quality','frequency','bitrate', \
            'lat', 'lon','download','upload','test-server-city','test-server-url', \
            'test-server-latency','bap-bssid','bap-rssi','bap-quality','bap-frequency']

    def __init__(self, wlan=None, test_runs=3):
        self.logfile = self.new_logfile()
        self.logwriter = csv.writer(self.logfile,delimiter=',',lineterminator='\n')
        self.spdtest = speedtest.Speedtest()
        self.spdtest.get_best_server()
        self.test_runs = test_runs
        self.wlan = wlan

        self.curr_log = {}
        self.curr_bap = {}

    def new_logfile(self):
        """ 
        Find a unique logfile name, open it, and return the file handle to it 
        """
        time.sleep(1)
        dt_stamp = self.get_timestamp()
        logfile = 'bwtest-{}-{}.log'.format(os.environ['USER'], \
            self.get_timestamp())

        if not os.path.isfile(logfile):
            return open(logfile,'w')

    def close_logfile(self):
        self.logfile.close()

    def flush_logfile(self):
        self.logfile.flush()

    def log_gps_coords(self, lat, lon):
        self.curr_log['lat'] = lat
        self.curr_log['lon'] = lon

    def new_logentry(self):
        self.curr_log = self.log_columns_dict.copy()
        self.curr_log['time'] = self.get_timestamp()
        self.curr_log['ssid'] = self.wlan.ssid()
        self.curr_log['bssid'] = self.wlan.ap_bssid()
        self.curr_log['rssi'] = self.wlan.ap_rssi()
        self.curr_log['quality'] = self.wlan.ap_quality()
        self.curr_log['frequency'] = self.wlan.ap_frequency()
        self.curr_log['bitrate'] = self.wlan.bitrate()
        self.curr_log['test-server-city'] = self.spdtest._best['name']
        self.curr_log['test-server-url'] = self.spdtest._best['url']
        self.curr_log['test-server-latency'] = self.spdtest._best['latency']

    def log_download_test(self):
        self.curr_log['download'] = self.run_download_test()

    def run_download_test(self):
        """
        Run download speed test an arbitrary amount and find sample mean
        """
        dl_rate = 0.0
        for run in range(self.test_runs):
            dl_rate += self.spdtest.download()
            time.sleep(1)

        return dl_rate / self.test_runs

    def log_upload_test(self):
        self.curr_log['upload'] = self.run_upload_test()

    def run_upload_test(self):
        """
        Run upload speed test an arbitrary amount and find sample mean
        """
        ul_rate = 0.0
        for run in range(self.test_runs):
            ul_rate += self.spdtest.upload()
            time.sleep(1)

        return ul_rate / self.test_runs

    def log_csv_header(self):
        """
        Return header row of CSV columns
        """
        self.logwriter.writerow(self.columns_order)
        self.flush_logfile()

    def log_scan_results(self):
        """ Write out scan results """
        self.logwriter.writerow([self.curr_log[key] for key in self.columns_order])
        self.flush_logfile()

    def log_better_ap(self):
        wdict = self.wlan.get_wlan_dict()
        bap = find_best_ap(wdict)
        if bap:
            self.curr_log['bap-bssid'] = bap['bssid']
            self.curr_log['bap-rssi'] = bap['rssi']
            self.curr_log['bap-quality'] = bap['quality']
            self.curr_log['bap-frequency'] = bap['frequency']

    @staticmethod
    def get_timestamp():
        """
        Time stamp in ISO format with seconds represented as whole numbers
        """
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())


class GpsdHandler(object):
    """
    Handler for the GPS daemon and functions depending on it
    """
    def __init__(self):
        """ Perform initial checks. Any failures raise an exception. """
        self.adb_forward_is_up()
        self.daemon_is_up()
        self.gpsd = gps(mode=WATCH_ENABLE)

    def adb_forward_is_up(self):
        output = subprocess.check_output("adb forward --list", shell=True).decode('utf-8')
        if 'tcp:4352 tcp:4352' not in output:
            raise GpsdAdbBridgeError('Missing ADB port forward')

    def daemon_is_up(self):
        output = subprocess.check_output("ps ax", shell=True).decode('utf-8')
        if 'gpsd tcp' not in output:
            raise GpsdProcessNotFound('Missing or invalid gpsd process')

    def get_gps_coords(self):
        """
        Obtain to GPS coordinates from gpsd. If unable to retrieve a
        Time, Position, Velocity (TPV) (i.e. no GPS lock) message after a certain
        number of attempts, raise an exception.
        """
        self.adb_forward_is_up()
        self.daemon_is_up()

        for attempts in range(0,15):
            report = self.gpsd.next()
            if report['class'] == 'TPV':
                lat = getattr(report,'lat',0.0)
                lon = getattr(report,'lon',0.0)
                break
        else:
            # Exhausted attempts, raise exception
            raise GpsdLockFailure('Unable to obtain GPS TPV message')

        return lat, lon


"""
Helper functions
"""
def main(wlan_card):
    wlan = Card(wlan_card)
    scan = ScanLog(wlan)
    scan.log_csv_header()

    try:
        gpsd = GpsdHandler()
    except (GpsdAdbBridgeError, GpsdProcessNotFound) as err:
        print(str(err))
        scan.close_logfile()
        sys.exit(1)


    # Main event loop
    run_scanner = True
    while run_scanner:
        scan.new_logentry()

        wifi_status_wrapper(wlan)
        gps_wrapper(gpsd, scan)

        display_menu = True
        while display_menu:
            menu()
            key = getch()

            # Parse selection
            if '\r' == key or '\n' == key:
                print('Running download test. Please be patient.')
                scan.log_download_test()
                print('Download test: COMPLETE')
                scan.log_upload_test()
                print('Running upload test. Please be patient.')
                print('Upload test: COMPLETE')
                print('Scanning for better AP on same radio band.')
                scan.log_better_ap()
                scan.log_scan_results()
                print('Logged scan results.\n')
                display_menu = False
            elif 'w' == key:
                wifi_status_wrapper(wlan)
            elif 'g' == key:
                gps_wrapper(gpsd, scan)
            elif '\x03' == key or 'x' == key: # ctrl-c
                display_menu = False
                run_scanner = False

    # Shutdown scanner
    print('Shutting down scanner.')
    scan.close_logfile()


def menu():
    prompt = """
    Enter: log speed test
    g: retry acquiring GPS lock
    w: re-scan WiFi device
    x: shutdown scanner
    """
    print(prompt)


def wifi_status_wrapper(wlan):
    try:
        print(wlan)
    except pyric.error as pyr_err:
        print('Pyric has communications from with the WiFi card.')
        print('Wait 30 seconds and try to re-scan the WiFi device')


def gps_wrapper(gpsd, scan):
    try:
        lat, lon = gpsd.get_gps_coords()
    except (GpsdAdbBridgeError, GpsdProcessNotFound) as err:
        print(err)
        scan.close_logfile()
        sys.exit(1)
    except GpsdLockFailure as lock_err:
        print(lock_err)
        print('Try repositioning phone. Refresh getting GPS')
    else:
        print('GPS coordinates logged.\nLAT: {}\nLON: {}'.format(lat,lon))
        scan.log_gps_coords(lat, lon)


def find_best_ap(wlan_dict):
    """
    Given current associated BSSID and signal at time of speed test, search for
    another AP with better characteristics.
    """
    cells = Cell.where(wlan_dict['interface'], find_eduroam)
    best_cell = None
    cell_dict = ScanLog.bap_columns_dict.copy()
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


def usage():
    sys.stderr.write("Usage: %s <wifi-interface>\n" % sys.argv[0])


if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)

    wlan_card = sys.argv[1]
    if not pyw.isinterface(wlan_card):
        err_msg("invalid wifi interface " + wlan_card)
        usage()
        sys.exit(1)

    main(wlan_card)


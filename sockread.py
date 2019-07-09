#!/usr/bin/env python

import io
import pynmea2
import socket

class SocketIO(io.RawIOBase):
    def __init__(self, sock):
        self.sock = sock
    def read(self, sz=-1):
        if (sz == -1): sz=0x00000100
        return self.sock.recv(sz)
    def seekable(self):
        return False


def receive_nmea(sck):
    buffer_size = 512
    fd = SocketIO(sck)  # fd can be used as an input file object

    try:
        for line in fd:
            if line.find('GGA') > 0:
                msg = pynmea2.parse(line)
                print('LAT: {}\tLON: {}'.format(msg.latitude, msg.longitude))
    except KeyboardInterrupt:
        print('tearing down socket')

    sck.close()


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = ('127.0.0.1', 4352)
sock.connect(server)

receive_nmea(sock)


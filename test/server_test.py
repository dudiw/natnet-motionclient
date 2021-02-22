import socket
import struct
import time
import os
import argparse

# Multicast address
MULTICAST_ADDRESS = '239.255.255.250'

# Broadcast interval in seconds. Use 0.01 for 10ms intervals (100 Hz)
INTERVAL = 10


class Server(object):
    """
    Mock server to test frame broadcast.
    The server must be initialized with the multicast address and the data_port used by the client.

    To obtain multicast address (Unix, MacOS):

    1. Ensure multicast is supported by the kernel and network interface
    1.a) In a terminal window, type ifconfig -a
    1.b) Look for en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
         The most important flag is MULTICAST appearing against your network interface.

    2. Check that multicast routing is configured
    2.a) In a terminal window, type netstat -nr
    2.b) Under 'Internet' routes table, look for IP in the range of 224.0.0.0-239.255.255.255
    2.c) If it doesn't appear, add a multicast address, for example:
         sudo route -nv add -net 228.0.0.4 -interface en0

    Attributes:
        multicast_address (str):
        data_port (int):
        command_port (int):
    """
    def __init__(self, multicast_address, data_port=1511, command_port=1510):
        self._multicast_address = multicast_address or MULTICAST_ADDRESS
        self._data_port = data_port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Set the time-to-live for messages to 1 so they do not go past the local network segment.
        ttl = struct.pack('B', 1)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def send_frame(self, frame):
        address = (self._multicast_address, self._data_port)
        self._socket.sendto(frame, address)


HINT_MULTICAST = 'The multicast IP.'
HINT_INTERVAL = 'The interval between messages, in seconds.'

if __name__ == '__main__':
    # Mock data frame
    root = os.path.dirname(__file__)
    frame = open(os.path.join(root, 'data', 'frame_packet_v3.bin'), 'rb').read()

    parser = argparse.ArgumentParser(description='Mock server that broadcasts test frames.')
    parser.add_argument('--multicast', type=str, default=MULTICAST_ADDRESS, help=HINT_MULTICAST)
    parser.add_argument('--interval', type=float, default=INTERVAL, help=HINT_INTERVAL)
    args = parser.parse_args()

    # Mock server
    server = Server(args.multicast)

    while True:
        server.send_frame(frame)
        time.sleep(args.interval)

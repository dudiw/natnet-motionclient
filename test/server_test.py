import socket
import struct
import time
import os

# Multicast address
MULTICAST_ADDRESS = '239.255.42.100'

# Broadcast interval in milliseconds
INTERVAL = 10


class Server(object):
    """
    Mock server to test frame broadcast.

    Attributes:
        multicast_address (str):
        data_port (int):
        command_port (int):
    """
    def __init__(self, multicast_address, data_port=1511, command_port=1510):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('', command_port))

        # Set the time-to-live for messages to 1 so they do not go past the local network segment.
        ttl = struct.pack('b', 1)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # Not the same as Motive default
        self._multicast_address = multicast_address or MULTICAST_ADDRESS
        self._data_port = data_port

    def send_frame(self, frame):
        address = (self._multicast_address, self._data_port)
        self._socket.sendto(frame, address)


if __name__ == '__main__':
    # Mock data frame
    root = os.path.dirname(__file__)
    frame = open(os.path.join(root, 'data', 'frame_packet_v3.bin'), 'rb').read()

    # Mock server
    server = Server(MULTICAST_ADDRESS)

    while True:
        server.send_frame(frame)
        time.sleep(INTERVAL)

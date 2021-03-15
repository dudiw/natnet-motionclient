import socket
from threading import Thread

from natnet.adapter import Adapter

# IP address of your local network interface.
IP_LOCAL = '127.0.0.1'

# Multicast address matching the multicast address listed in Motive streaming settings.
IP_MULTICAST = '239.255.255.250'

# NatNet Data channel
PORT_DATA = 1511

# IP address of the NatNet server.
IP_SERVER = '127.0.0.1'

# NatNet Command channel
PORT_COMMAND = 1510

# 32k byte buffer size
SIZE_BUFFER = 32768


class MotionClient(object):
    """
    Client for NatNet protocol.
    The client must be initialized with the multicast address and the data_port matching the server

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
        ip_local (str): IP address of your local network interface.
        ip_multicast (str): Multicast address matching the multicast address listed in Motive streaming settings.
        port_data (int): NatNet Data channel.
        ip_server (str): IP address of the NatNet server.
        port_command (int): NatNet Command channel.
    """
    def __init__(self, listener, ip_local, ip_multicast=IP_MULTICAST, port_data=PORT_DATA,
                 ip_server=IP_SERVER, port_command=PORT_COMMAND):

        self._local_ip = ip_local
        self._multicast_ip = ip_multicast
        self._data_port = port_data
        self._data_socket = None
        self._data_thread = None

        self._server_ip = ip_server
        self._command_port = port_command
        self._command_socket = None
        self._command_thread = None

        self._is_running = False

        self._adapter = Adapter(listener)

    def get_data(self):
        """
        Start streaming motion capture data.
        Data frames are delivered to `MotionListener` until `MotionClient.disconnect()` is called.
        """
        self._send_command(self._adapter.get_data())

    def get_version(self):
        """
        Request software version details from the Motion Server.
        """
        self._send_command(self._adapter.get_version())

    def get_descriptors(self):
        self._send_command(self._adapter.get_descriptors())

    def get_nat(self, command_string):
        self._send_command(self._adapter.get_nat(command_string))

    def connect(self):
        """ Connect to NatNet server """
        if self._is_running:
            return

        # Create the command and data sockets
        self._data_socket = self._create_data_socket(self._data_port)
        if not self._data_socket:
            print('Could not open data channel')
            return

        self._command_socket = self._create_command_socket()
        if not self._command_socket:
            print('Could not open command channel')
            self._close_socket(self._data_socket)
            return

        self._is_running = True

        # Create a separate thread for receiving data packets
        self._data_thread = Thread(target=self._data_callback, args=(self._data_socket,))
        self._data_thread.start()

        # Create a separate thread for receiving command packets
        self._command_thread = Thread(target=self._data_callback, args=(self._command_socket,))
        self._command_thread.start()

    def disconnect(self):
        """ Disconnect from NatNet server. """
        if self._is_running:
            self._is_running = False
            self._data_thread.join()

            self._send_command(self._adapter.get_disconnect())
            self._command_thread.join()

    def _create_command_socket(self):
        """ Create a command socket to attach to the NatNet stream. """
        socket_command = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_command.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_command.bind(('', 0))
        socket_command.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        socket_command.setblocking(True)
        return socket_command

    def _send_command(self, data):
        self.connect()
        address = (self._server_ip, self._command_port)
        self._command_socket.sendto(data, address)

    def _create_data_socket(self, port):
        """ Create a data socket (UDP) to attach to the NatNet stream. """

        # TODO: check data socket creation issues:
        #  https://github.com/ricardodeazambuja/OptiTrackPython/blob/master/OptiTrackPython.py
        #  https://github.com/paparazzi/paparazzi/blob/master/sw/ground_segment/python/natnet3.x/NatNetClient.py

        # create UDP socket
        socket_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            socket_data.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass

        socket_data.bind((self._multicast_ip, port))

        client_ip = self._local_ip or socket.gethostbyname(socket.gethostname())

        client = socket.inet_aton(client_ip)
        membership = socket.inet_aton(self._multicast_ip) + client
        socket_data.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, client)
        socket_data.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, membership)
        return socket_data

    def _data_callback(self, data_socket, timeout=0.1):
        """ Continuously receive and process messages. """

        self._clear_buffer(data_socket)

        # prevent recv from block indefinitely
        data_socket.settimeout(timeout)

        while self._is_running:
            try:
                data = data_socket.recv(SIZE_BUFFER)
                if len(data):
                    self._adapter.process_message(data)
            except (KeyboardInterrupt, SystemExit, OSError):
                print('Exiting data socket')

            except socket.timeout:
                print('NatNetClient socket timeout!')
                continue

        self._close_socket(data_socket)

    def _clear_buffer(self, data_socket):
        """ Clear pending messages from receiving buffer """

        # attempt to read a 1 byte length messages without blocking.
        # recv throws an exception as it fails to receive data from the cleared buffer
        while True:
            try:
                data_socket.recv(1, socket.MSG_DONTWAIT)
            except IOError:
                break

    def _close_socket(self, data_socket):
        if not data_socket:
            return

        # drop membership
        try:
            membership = socket.inet_aton(self._multicast_ip) + socket.inet_aton('0.0.0.0')
            data_socket.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, membership)
        except socket.error:
            pass

        # close socket
        try:
            data_socket.close()
        except socket.error as err:
            print('Closing socket failed {}'.format(err))

    def __del__(self):
        self.disconnect()

import socket
from threading import Thread

from natnet.adapter import Adapter

# IP address of your local network interface.
IP_LOCAL = '127.0.0.1'

# Multicast address matching the multicast address listed in Motive streaming settings.
IP_MULTICAST = '239.255.42.99'

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
                 ip_server=IP_SERVER, port_command=PORT_COMMAND, verbose=False):

        self._verbose = verbose
        self._local_ip = ip_local
        self._multicast_ip = ip_multicast
        self._data_port = port_data
        self._data_socket = None
        self._data_thread = None

        self._server_ip = ip_server
        self._command_port = port_command
        self._command_socket = None
        self._command_thread = None

        self._adapter = Adapter(listener, verbose)

        self._is_running = False

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

    def _connect(self):
        """ Connect to NatNet server """
        if self._is_running:
            return

        # Create thread for receiving motion capture data
        self._data_thread = DataThread(self._adapter, self._local_ip, self._multicast_ip, self._data_port)
        self._data_thread.daemon = True
        self._data_thread.start()

        # Create thread for sending commands and receiving result
        self._command_thread = CommandThread(self._adapter, self._server_ip, self._command_port)
        self._command_thread.daemon = True
        self._command_thread.start()

        self._is_running = True

    def disconnect(self):
        """ Disconnect from NatNet server. """
        if self._is_running:
            self._is_running = False

            self._data_thread.stop()
            self._command_thread.stop()

    def _send_command(self, data):
        self._connect()
        self._command_thread.send(data)

    def _print(self, message):
        if self._verbose:
            print(message)

    def __del__(self):
        self.disconnect()


# TODO: check data socket creation issues:
#  https://github.com/ricardodeazambuja/OptiTrackPython/blob/master/OptiTrackPython.py
#  https://github.com/paparazzi/paparazzi/blob/master/sw/ground_segment/python/natnet3.x/NatNetClient.py
class DataThread(Thread):

    TIMEOUT = 0.2

    def __init__(self, adapter, local_ip, multicast_ip, port):
        Thread.__init__(self)

        self._adapter = adapter
        self._socket = None
        self._multicast_ip = multicast_ip
        self._local_ip = local_ip
        self._port = port
        self._is_running = False

    def run(self):
        """ Continuously receive and process messages. """
        self._create_data_socket()

        self._is_running = True

        # self._clear_buffer(data_socket)

        # prevent recv from block indefinitely
        self._socket.settimeout(DataThread.TIMEOUT)

        while self._is_running:
            try:
                data = self._socket.recv(SIZE_BUFFER)
                if len(data):
                    self._adapter.process_message(data)
            except (KeyboardInterrupt, SystemExit, OSError):
                print('Exiting data socket')

            except socket.timeout:
                print('NatNetClient data socket timeout!')
                continue

        self._close_socket()

    def _create_data_socket(self):
        """ Create a data socket (UDP) to attach to the NatNet stream. """
        self._close_socket()

        # create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass

        membership = socket.inet_aton(self._multicast_ip) + socket.inet_aton(self._local_ip)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        self._socket.bind((self._local_ip, self._port))
        return self._socket

    def _clear_buffer(self, data_socket):
        """ Clear pending messages from receiving buffer """

        # attempt to read a 1 byte length messages without blocking.
        # recv throws an exception as it fails to receive data from the cleared buffer
        data_socket.setblocking(False)
        while True:
            try:
                data_socket.recv(1)
            except IOError:
                break
        data_socket.setblocking(True)

    def stop(self, timeout=0.1):
        self._is_running = False
        self._close_socket()
        self.join(timeout)

    def _close_socket(self):
        if not self._socket:
            return

        # drop membership
        try:
            membership = socket.inet_aton(self._multicast_ip) + socket.inet_aton('0.0.0.0')
            self._socket.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP, membership)
        except socket.error:
            pass

        # close socket
        try:
            self._socket.close()
        except socket.error as err:
            print('Closing socket failed {}'.format(err))


class CommandThread(Thread):

    TIMEOUT = 0.2

    def __init__(self, adapter, server_ip, port):
        Thread.__init__(self)
        self._adapter = adapter
        self._socket = None
        self._server_ip = server_ip
        self._port = port

        self._is_running = False

    def send(self, data):
        address = (self._server_ip, self._port)
        self._create_command_socket()
        self._socket.sendto(data, address)

    def run(self):
        """ Continuously receive and process messages. """
        self._create_command_socket()

        self._is_running = True

        # self._clear_buffer(data_socket)

        # prevent recv from block indefinitely
        self._socket.settimeout(DataThread.TIMEOUT)

        while self._is_running:
            try:
                data = self._socket.recv(SIZE_BUFFER)
                if len(data):
                    self._adapter.process_message(data)
            except (KeyboardInterrupt, SystemExit, OSError):
                print('Exiting data socket')

            except socket.timeout:
                print('NatNetClient command socket timeout!')
                continue

        self._close_socket()

    def _create_command_socket(self):
        """ Create a command socket to attach to the NatNet stream. """
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(('', 0))
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.setblocking(True)
        return self._socket

    def _clear_buffer(self, data_socket):
        """ Clear pending messages from receiving buffer """

        # attempt to read a 1 byte length messages without blocking.
        # recv throws an exception as it fails to receive data from the cleared buffer
        data_socket.setblocking(False)
        while True:
            try:
                data_socket.recv(1)
            except IOError:
                break
        data_socket.setblocking(True)

    def stop(self, timeout=0.1):
        self.send(self._adapter.get_disconnect())

        self._is_running = False
        self._close_socket()
        self.join(timeout)

    def _close_socket(self):
        if not self._socket:
            return

        # close socket
        try:
            self._socket.close()
        except socket.error as err:
            print('Closing socket failed {}'.format(err))

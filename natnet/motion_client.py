import socket
from threading import Thread

from natnet.adapter import Adapter

# Change this value to the IP address of the NatNet server.
IP_SERVER = '127.0.0.1'

# Change this value to the IP address of your local network interface
IP_LOCAL = '127.0.0.1'

# This should match the multicast address listed in Motive's streaming settings.
IP_MULTICAST = '239.255.42.99'

# NatNet Command channel
PORT_COMMAND = 1510

# NatNet Data channel
PORT_DATA = 1511

# 32k byte buffer size
SIZE_BUFFER = 32768


class MotionClient(object):
    def __init__(self, listener, ip_server=IP_SERVER, ip_local=IP_LOCAL,
                 ip_multicast=IP_MULTICAST, port_command=PORT_COMMAND, port_data=PORT_DATA):

        self._server_ip = ip_server
        self._local_ip = ip_local
        self._multicast_ip = ip_multicast

        self._command_port = port_command
        self._data_port = port_data

        self._data_socket = None
        self._data_thread = None

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
        self._command_socket = self._create_command_socket()
        if not self._data_socket or not self._command_socket:
            print('Could not open command/data channel')
            self._close_sockets()
            return

        self._is_running = True

        # Create a separate thread for receiving data packets
        self._data_thread = Thread(target=self._data_callback, args=(self._data_socket,))
        self._data_thread.start()

        # Create a separate thread for receiving command packets
        self._command_thread = Thread(target=self._data_callback, args=(self._command_socket,))
        self._command_thread.start()

    def disconnect(self):
        """ Disconnect from NatNet server """
        if not self._is_running:
            return
        self._is_running = False
        self._close_sockets()

    def _close_sockets(self):
        # Close data socket
        if self._data_socket:
            try:
                self._data_socket.close()
            except socket.error as err:
                print('Closing data socket failed {}'.format(err))
        self._data_socket = None

        # Close command socket
        if self._command_socket:
            try:
                self._command_socket.close()
            except socket.error as err:
                print('Closing command socket failed {}'.format(err))

        self._command_socket = None

    # Create a data socket (UDP) to attach to the NatNet stream
    def _create_data_socket(self, port):
        value = socket.inet_aton(self._multicast_ip) + socket.inet_aton(self._local_ip)

        result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, value)
        result.bind((self._local_ip, port))
        return result

    # Create a command socket to attach to the NatNet stream
    def _create_command_socket(self):
        result = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        result.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result.bind(('', 0))
        result.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return result

    def _data_callback(self, data_socket):
        """Continuously receive and process messages."""
        try:
            while self._is_running:
                # Blocking network call
                data, addr = data_socket.recv(SIZE_BUFFER)
                if len(data):
                    self._adapter.process_message(data)
        except (KeyboardInterrupt, SystemExit):
            print('Exiting')

    def _send_command(self, data):
        self.connect()
        address = (self._server_ip, self._command_port)
        self._command_socket.sendto(data, address)

    def __del__(self):
        self._close_sockets()

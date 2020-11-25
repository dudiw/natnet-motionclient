import struct

from typing import List
from natnet.protocol import Protocol, LabeledMarker, RigidBody, Skeleton, TimeInfo

# Client/server message ids
NAT_PING = 0
NAT_PING_RESPONSE = 1
NAT_REQUEST = 2
NAT_RESPONSE = 3
NAT_REQUEST_MODEL_DEF = 4
NAT_MODEL_DEF = 5
NAT_REQUEST_FRAME_OF_DATA = 6
NAT_FRAME_OF_DATA = 7
NAT_MESSAGE_STRING = 8
NAT_DISCONNECT = 9
NAT_UNRECOGNIZED_REQUEST = 0x100

# Description types
TYPE_MARKERS = 0
TYPE_RIGID_BODY = 1
TYPE_SKELETON = 2


class MotionListener:
    def on_version(self, version: tuple):
        """
        Callback for NatNet version query.
        :param version: (str) Version tuple ('major', 'minor', 'build', 'revision').
        """
        pass

    def on_rigid_body(self, bodies: List[RigidBody], time_info: TimeInfo):
        """Callback for NatNet rigid body update. It is called once per frame.
        :param bodies: a list of RigidBody elements, each with id, Position and Rotation
        :param time_info: time as a TimeInfo element
        """
        pass

    def on_skeletons(self, skeletons: List[Skeleton], time_info: TimeInfo):
        """
        Callback for NatNet skeleton update. It is called once per frame.
        :param skeletons: a list of Skeletons elements, each with id, and a list of Markers
        :param time_info: time as a TimeInfo element
        """
        pass

    def on_labeled_markers(self, markers: List[LabeledMarker], time_info: TimeInfo):
        """
        Callback for NatNet labeled markers update. It is called once per frame.
        :param markers: a list of LabeledMarker elements, each with id, and Position
        :param time_info: time as a TimeInfo element
        """
        pass

    def on_unlabeled_marker(self, marker):
        pass


class Adapter:
    def __init__(self, listener: MotionListener):
        self._listener = listener or MotionListener()
        self._protocol = Protocol()

    # Unpack data from a motion capture frame message
    def _unpack_motion_capture(self, data):
        print("Begin MoCap Frame\n-----------------\n")

        # access the internal buffers of an object
        data = memoryview(data)
        offset = 0

        # Frame number (4 bytes)
        frame_number = self._protocol.read_int(data, offset)
        offset += 4
        print(f'Frame #: {frame_number}')

        # Marker sets
        shift, marker_sets = self._protocol.unpack_marker_sets(data[offset:])
        offset += shift

        # Unlabeled markers
        shift, unlabeled_markers = self._protocol.unpack_positions(data[offset:])
        offset += shift
        print(f'Unlabeled Markers Count: {len(unlabeled_markers)}')

        # Rigid bodies
        shift, rigid_bodies = self._protocol.unpack_rigid_bodies(data[offset:])
        offset += shift
        print(f'Rigid Body Count: {rigid_bodies}')

        # Skeletons (Version 2.1 and later)
        shift, skeletons = self._protocol.unpack_skeletons(data[offset:])
        offset += shift
        print(f'Skeleton Count: {len(skeletons)}')

        # Labeled markers (Version 2.3 and later)
        shift, labeled_markers = self._protocol.unpack_labeled_markers(data[offset:])
        offset += shift
        print(f'Labeled Marker Count: {labeled_markers}')

        # Force Plate data (version 2.9 and later)
        shift, force_plates = self._protocol.unpack_force_plates(data[offset:])
        offset += shift
        print(f'Force Plate Count: {force_plates}')

        # Device data (version 2.11 and later) - same structure as Force Plates
        shift, devices = self._protocol.unpack_force_plates(data[offset:])
        offset += shift
        print(f'Device Count: {devices}')

        # Time information
        shift, time_info = self._protocol.unpack_time_info(data[offset:])
        offset += shift
        print(f'Time: {time_info.timestamp}')

        # Frame parameters
        param, = struct.unpack('h', data[offset:offset + 2])
        is_recording = (param & 0x01) != 0
        tracked_models_changed = (param & 0x02) != 0
        offset += 2

        # Send rigid body to listener
        self._listener.on_rigid_body(rigid_bodies, time_info)

        # Send skeletons to listener
        self._listener.on_skeletons(skeletons, time_info)

        # Send labeled markers to listener
        self._listener.on_labeled_markers(labeled_markers, time_info)

    # Unpack a data description packet
    def _unpack_description(self, data):
        offset = 0
        items = self._protocol.read_int(data, offset)
        offset += 4

        for i in range(0, items):
            description_type = self._protocol.read_int(data, offset)
            offset += 4
            if description_type == TYPE_MARKERS:
                offset += self._protocol.unpack_marker_set_description(data[offset:])
            elif description_type == TYPE_RIGID_BODY:
                offset += self._protocol.unpack_rigid_body_description(data[offset:])
            elif description_type == TYPE_SKELETON:
                offset += self._protocol.unpack_skeleton_description(data[offset:])

    def process_message(self, data):
        print("Begin Packet\n------------\n")

        message_id = int.from_bytes(data[0:2], byteorder='little')
        print(f'Message ID: {message_id}')

        packet_size = int.from_bytes(data[2:4], byteorder='little')
        print(f'Packet Size: {packet_size}')

        offset = 4
        if message_id == NAT_FRAME_OF_DATA:
            self._unpack_motion_capture(data[offset:])
        elif message_id == NAT_MODEL_DEF:
            self._unpack_description(data[offset:])
        elif message_id == NAT_PING_RESPONSE or message_id == NAT_PING:
            version = self._protocol.unpack_version(data[offset:])
            self._listener.on_version(version)
        elif message_id == NAT_RESPONSE:
            if packet_size == 4:
                command_response = self._protocol.read_int(data, offset)
                offset += 4
            else:
                message, separator, remainder = bytes(data[offset:]).partition(b'\0')
                offset += len(message) + 1
                print(f'Command response: {message.decode("utf-8")}')
        elif message_id == NAT_UNRECOGNIZED_REQUEST:
            print("Received 'Unrecognized request' from server")
        elif message_id == NAT_MESSAGE_STRING:
            message, separator, remainder = bytes(data[offset:]).partition(b'\0')
            offset += len(message) + 1
            print(f'Received message from server: {message.decode("utf-8")}')
        else:
            print("ERROR: Unrecognized packet type")

        print("End Packet\n----------\n")

    def get_version(self):
        command_string = 'Ping'
        packet_size = len(command_string) + 1
        return self._protocol.get_request_payload(NAT_PING, command_string, packet_size)

    def get_nat(self, command_string):
        packet_size = len(command_string) + 1
        return self._protocol.get_request_payload(NAT_REQUEST, command_string, packet_size)

    def get_data(self):
        return self._protocol.get_request_payload(NAT_REQUEST_FRAME_OF_DATA, '', 0)

    def get_descriptors(self):
        return self._protocol.get_request_payload(NAT_REQUEST_MODEL_DEF, '', 0)

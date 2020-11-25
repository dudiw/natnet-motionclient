from natnet.protocol import Protocol, UIntValue, ShortValue, UShortValue

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


class MotionListener(object):
    def on_version(self, version):
        """
        Callback for NatNet version query.
        Args:
             version (:class:`Version`): Motion Server version ['major', 'minor', 'build', 'revision'].
        """
        pass

    def on_rigid_body(self, bodies, time_info):
        """
        Callback for NatNet rigid bodies update. It is called once per frame.
        Args:
            bodies (list[:class:`RigidBody`]): a list of RigidBody elements, each with id, Position and Rotation
            time_info (:class:`TimeInfo`): time as a TimeInfo element
        """
        pass

    def on_skeletons(self, skeletons, time_info):
        """
        Callback for NatNet skeletons update. It is called once per frame.

        Args:
            skeletons (list[:class:`Skeleton`]) a list of Skeletons elements, each with id, and a list of RigidBodies
            time_info (:class:`TimeInfo`): time as a TimeInfo element
        """
        pass

    def on_labeled_markers(self, markers, time_info):
        """
        Callback for NatNet labeled markers update. It is called once per frame.

        Args:
            markers (list[:class:`LabeledMarker`]): a list of LabeledMarker elements, each with id, and Position
            time_info (:class:`TimeInfo`): time as a TimeInfo element
        """
        pass

    def on_unlabeled_markers(self, markers, time_info):
        """
        Callback for NatNet unlabeled markers update. It is called once per frame.

        Args:
            markers (list[:class:`Position`]): a list of Position elements of unlabeled marker
            time_info (:class:`TimeInfo`): time as a TimeInfo element
        """
        pass


class Adapter(object):
    def __init__(self, listener):
        """
        Converts NatNet payload into python elements.

        Args:
             listener (:class:`MotionListener`): a listener invoked by new data frames
        """
        self._listener = listener or MotionListener()
        self._protocol = Protocol()

    # Unpack data from a motion capture frame message
    def _unpack_motion_capture(self, data):
        print("Begin MoCap Frame\n-----------------\n")

        # access the internal buffers of an object
        data = memoryview(data)
        offset = 0

        # Frame number
        shift, frame_number = self._protocol.read_value(data, offset, UIntValue)
        offset += shift
        print('Frame #: {}'.format(frame_number))

        # Marker sets
        shift, marker_sets = self._protocol.unpack_marker_sets(data[offset:])
        offset += shift

        # Unlabeled markers
        shift, unlabeled_markers = self._protocol.unpack_positions(data[offset:])
        offset += shift

        # Rigid bodies
        shift, rigid_bodies = self._protocol.unpack_rigid_bodies(data[offset:])
        offset += shift

        # Skeletons (Version 2.1 and later)
        shift, skeletons = self._protocol.unpack_skeletons(data[offset:])
        offset += shift

        # Labeled markers (Version 2.3 and later)
        shift, labeled_markers = self._protocol.unpack_labeled_markers(data[offset:])
        offset += shift

        # Force Plate data (version 2.9 and later)
        shift, force_plates = self._protocol.unpack_force_plates(data[offset:])
        offset += shift
        if force_plates:
            print('Force Plate Count: {}'.format(force_plates))

        # Device data (version 2.11 and later) - same structure as Force Plates
        shift, devices = self._protocol.unpack_force_plates(data[offset:])
        offset += shift
        if devices:
            print('Device Count: {}'.format(devices))

        # Time information
        shift, time_info = self._protocol.unpack_time_info(data[offset:])
        offset += shift

        # Frame parameters
        shift, param = self._protocol.read_value(data, offset, ShortValue)
        offset += shift
        is_recording = (param & 0x01) != 0
        tracked_models_changed = (param & 0x02) != 0

        # Send rigid body to listener
        self._listener.on_rigid_body(rigid_bodies, time_info)

        # Send skeletons to listener
        self._listener.on_skeletons(skeletons, time_info)

        # Send labeled markers to listener
        self._listener.on_labeled_markers(labeled_markers, time_info)

        # Send unlabeled markers to listener
        self._listener.on_unlabeled_markers(unlabeled_markers, time_info)

    # Unpack a data description packet
    def _unpack_description(self, data):
        offset = 0
        shift, items = self._protocol.read_value(data, offset, UIntValue)
        offset += shift

        for i in range(0, items):
            shift, description_type = self._protocol.read_value(data, offset, UIntValue)
            offset += shift
            if description_type == TYPE_MARKERS:
                offset += self._protocol.unpack_marker_set_description(data[offset:])
            elif description_type == TYPE_RIGID_BODY:
                offset += self._protocol.unpack_rigid_body_description(data[offset:])
            elif description_type == TYPE_SKELETON:
                offset += self._protocol.unpack_skeleton_description(data[offset:])

    def process_message(self, data):
        print("Begin Packet\n------------\n")
        offset = 0
        shift, message_id = self._protocol.read_value(data, offset, UShortValue)
        offset += shift
        print('Message ID: {}'.format(message_id))

        shift, packet_size = self._protocol.read_value(data, offset, UShortValue)
        print('Packet Size: {}'.format(packet_size))
        offset += shift

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
                shift, command_response = self._protocol.read_value(data, offset, UIntValue)
                offset += shift
            else:
                shift, message = self._protocol.read_string(data, offset)
                offset += shift
                print('Command response: {}'.format(message))
        elif message_id == NAT_UNRECOGNIZED_REQUEST:
            print("Received 'Unrecognized request' from server")
        elif message_id == NAT_MESSAGE_STRING:
            shift, message = self._protocol.read_string(data, offset)
            print('Received message from server: {}'.format(message))
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

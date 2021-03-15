import struct

# Structs object types
ShortValue = struct.Struct('<h')
IntValue = struct.Struct('<i')
UShortValue = struct.Struct('<H')
UIntValue = struct.Struct('<I')
ULongValue = struct.Struct('<Q')
FloatValue = struct.Struct('<f')
DoubleValue = struct.Struct('<d')
Vector3 = struct.Struct('<fff')
Quaternion = struct.Struct('<ffff')
VERSION = 'BBBB'


class Version(object):
    """
    NatNet version

    Attributes:
        major (int):
        minor (int):
        build (int):
        revision (int):
    """
    def __init__(self, major, minor, build, revision):
        self.major = major
        self.minor = minor
        self.build = build
        self.revision = revision

    def __repr__(self):
        return 'Version(major={}, minor={}, build={}, revision={})'.format(self.major, self.minor, self.build, self.revision)


class Position(object):
    """
    Position in 3D space

    Attributes:
        x (float):
        y (float):
        z (float):
    """
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return 'Position(x={}, y={}, z={})'.format(self.x, self.y, self.z)


class Rotation(object):
    """
    Rotation quaternion

    Attributes:
        w (float):
        x (float):
        y (float):
        z (float):
    """
    def __init__(self, w, x, y, z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        return 'Rotation(w={}, x={}, y={}, z={})'.format(self.w, self.x, self.y, self.z)


class LabeledMarker(object):
    """
    Labeled marker

    Attributes:
        name (int): the marker id
        position (:class:`Position`): marker position
    """
    def __init__(self, name, position):
        self.name = name
        self.position = position

    def __repr__(self):
        return 'LabeledMarker(name={}, position={})'.format(self.name, self.position)


class MarkerSet(object):
    """
    Marker Set of several Position elements

    Attributes:
        name (str): the marker set name
        positions (list[:class:`Position`]): a list of marker positions position
    """
    def __init__(self, name, positions):
        self.name = name
        self.positions = positions

    def __repr__(self):
        return 'MarkerSet(name={}, positions={})'.format(self.name, self.positions)


class RigidBody(object):
    """
    Rigid Body element with id, position and rotation

    Attributes:
        body_id (int): the marker set name
        position (:class:`Position`): the rigid body position
        rotation (:class:`Rotation`): the rigid body rotation
    """
    def __init__(self, body_id, position, rotation):
        self.body_id = body_id
        self.position = position
        self.rotation = rotation

    def __repr__(self):
        return 'RigidBody(body_id={}, position={}, rotation={})'.format(self.body_id, self.position, self.rotation)


class Skeleton(object):
    """
    A skeleton composed of rigid body elements

    Attributes:
        skeleton_id (str): the marker set name
        rigid_bodies (list[:class:`RigidBody`]): a list of rigid bodies
    """
    def __init__(self, skeleton_id, rigid_bodies):
        self.skeleton_id = skeleton_id
        self.rigid_bodies = rigid_bodies

    def __repr__(self):
        return 'Skeleton(skeleton_id={}, rigid_bodies={})'.format(self.skeleton_id, self.rigid_bodies)


class ForcePlate(object):
    """
    A force plate

    Attributes:
        plate_id (int): the marker set name
        channels (list[list[int]]): a list analog channels
    """
    def __init__(self, plate_id, channels):
        self.plate_id = plate_id
        self.channels = channels

    def __repr__(self):
        return 'ForcePlate(plate_id={}, channels={})'.format(self.plate_id, self.channels)


class TimeInfo(object):
    """
    A time information element detailing the timestamp and high-resolution time

    Attributes:
        timestamp (float): the frame timestamp in seconds since software startup
        time_code (int): SMPTE timecode
        time_sub_code (int): SMPTE timecode subframe
        time_camera_exposure (int): Camera mid exposure time (in performance counter ticks)
        time_data_received (int): Time camera data was received (in performance counter ticks)
        time_transmit (int): Time frame was transmitted (in performance counter ticks)
    """
    def __init__(self, timestamp, time_code, time_sub_code, time_camera_exposure, time_data_received, time_transmit):
        self.timestamp = timestamp
        self.time_code = time_code
        self.time_sub_code = time_sub_code
        self.time_camera_exposure = time_camera_exposure
        self.time_data_received = time_data_received
        self.time_transmit = time_transmit

    def __repr__(self):
        return 'TimeInfo(timestamp={}, time_code={}, time_sub_code={}, ' \
               'time_camera_exposure={}, time_data_received={}, time_transmit={})'\
            .format(self.timestamp, self.time_code, self.time_sub_code,
                    self.time_camera_exposure, self.time_data_received, self.time_transmit)


class Protocol(object):
    def read_string(self, data, offset):
        """
        Unpack a null-terminated string field.

        Args:
            data (bytes):
            offset (int):
        Returns:
            shift (int):
            value (str):
        """
        value, separator_, remainder_ = bytes(data[offset:]).partition(b'\0')
        shift = len(value) + 1
        value = value.decode('utf-8')
        return shift, value

    def read_value(self, data, offset, struct_type):
        """
        Unpack value.

        Args:
            data:
            offset (int):
            struct_type (struct.Struct):
        Returns:
            shift (int):
            value (int):
        """
        shift = struct_type.size
        value = struct_type.unpack(data[offset:offset + shift])
        if len(value) == 1:
            value = value[0]
        return shift, value

    def unpack_positions(self, data):
        """Unpack a list of positions.

        Args:
            data (bytes):
        Returns:
            offset (int):
            markers (list[:class:`Position`]): a list of marker Positions
        """
        offset = 0

        # Marker count (4 bytes)
        shift, marker_count = self.read_value(data, offset, UIntValue)
        offset += shift
        markers = []
        for j in range(0, marker_count):
            shift, pos = self.read_value(data, offset, Vector3)
            offset += shift
            markers.append(Position(*pos))
        return offset, markers

    def _unpack_rigid_body(self, data):
        """
        Unpack a rigid body object from a data packet

        Args:
            data (bytes):
        Returns:
            shift (int):
            rigid_body (:class:`RigidBody`): a RigidBody element
        """
        offset = 0

        # ID (4 bytes)
        shift, body_id = self.read_value(data, offset, UIntValue)
        offset += shift

        # Position and orientation
        shift, pos = self.read_value(data, offset, Vector3)
        offset += shift
        position = Position(*pos)
        shift, rot = self.read_value(data, offset, Quaternion)
        offset += shift
        rotation = Rotation(*rot)

        # Version 2 and later
        shift, marker_error = self.read_value(data, offset, FloatValue)
        offset += shift
        print('Marker Error: {}'.format(marker_error))

        # Version 2.6 and later
        shift, param = self.read_value(data, offset, ShortValue)
        offset += shift
        tracking_valid = (param & 0x01) != 0
        print('Tracking Valid: {}'.format(tracking_valid))

        rigid_body = RigidBody(body_id, position, rotation)

        return offset, rigid_body

    def unpack_rigid_bodies(self, data):
        """
        Unpack a rigid body object from a data packet

        Args:
            data (bytes):
        Returns:
            shift (int):
            rigid_bodies (list[:class:`RigidBody`]): a list of RigidBody elements
        """
        offset = 0
        shift, rigid_body_count = self.read_value(data, offset, UIntValue)
        offset += shift

        rigid_bodies = list()
        for i in range(0, rigid_body_count):
            shift, rigid_body = self._unpack_rigid_body(data[offset:])
            rigid_bodies.append(rigid_body)
            offset += shift

        return offset, rigid_bodies

    def _unpack_skeleton(self, data):
        """
        Unpack a skeleton object from a data packet.

        Args:
            data (bytes):
        Returns:
            shift (int):
            skeleton (:class:`Skeleton`): a Skeleton element
        """
        offset = 0

        shift, skeleton_id = self.read_value(data, offset, UIntValue)
        offset += shift
        print('ID {}'.format(skeleton_id))

        shift, bodies = self.unpack_rigid_bodies(data[offset:])
        offset += shift

        return offset, Skeleton(skeleton_id, bodies)

    def unpack_skeletons(self, data):
        """
        Unpack skeletons.

        Args:
            data (bytes):
        Returns:
            shift (int):
            skeletons (list[:class:`Skeleton`]): a list of Skeleton elements
        """
        offset = 0
        shift, skeleton_count = self.read_value(data, offset, UIntValue)
        offset += shift
        print('Skeleton Count: {}'.format(skeleton_count))

        skeletons = []
        for i in range(0, skeleton_count):
            shift, skeleton = self._unpack_skeleton(data[offset:])
            skeletons[skeleton.skeleton_id] = skeleton
            offset += shift

        return offset, skeletons

    def unpack_marker_sets(self, data):
        """
        Unpack marker sets

        Args:
            data (bytes):
        Returns:
            shift (int):
            marker_sets (list[:class:`MarkerSet`]): a list of MarkerSet elements
        """
        offset = 0
        shift, marker_set_count = self.read_value(data, offset, UIntValue)
        offset += shift
        print('Marker Set Count: {}'.format(marker_set_count))

        marker_sets = []

        for i in range(0, marker_set_count):
            # Model name
            shift, model_name = self.read_string(data, offset)
            offset += shift
            print('Model Name: {}'.format(model_name))

            shift, positions = self.unpack_positions(data[offset:])
            marker_sets.append(MarkerSet(model_name, positions))
            offset += shift

        return offset, marker_sets

    def unpack_labeled_markers(self, data):
        """
        Args:
            data (bytes):
        Returns:
            shift (int):
            markers (list[:class:`LabeledMarker`]) a list of LabeledMarker elements
        """
        offset = 0
        shift, labeled_marker_count = self.read_value(data, offset, UIntValue)
        offset += shift

        labeled_markers = []
        for i in range(0, labeled_marker_count):
            shift, marker_id = self.read_value(data, offset, UIntValue)
            offset += shift
            shift, pos = self.read_value(data, offset, Vector3)
            offset += shift
            position = Position(*pos)
            shift, size = self.read_value(data, offset, FloatValue)
            offset += shift

            # Version 2.6 and later
            shift, param = self.read_value(data, offset, ShortValue)
            offset += shift
            occluded = (param & 0x01) != 0
            point_cloud_solved = (param & 0x02) != 0
            model_solved = (param & 0x04) != 0

            # Version 3.0 and later
            shift, residual = self.read_value(data, offset, FloatValue)
            offset += shift

            labeled_markers.append(LabeledMarker(marker_id, position))

        return offset, labeled_markers

    def unpack_force_plates(self, data):
        """
        Unpacks Force Plate elements.

        Args:
            data: (bytes):
        Return:
            shift (int):
            devices (list[:class:`Devices`]): a list of device elements
        """
        offset = 0
        shift, plate_count = self.read_value(data, offset, UIntValue)
        offset += shift
        force_plates = []
        for i in range(0, plate_count):
            # ID
            shift, plate_id = self.read_value(data, offset, UIntValue)
            offset += shift

            # Channel Count
            shift, plate_channels = self.read_value(data, offset, UIntValue)
            offset += shift

            channels = []
            # Channel Data
            for j in range(0, plate_channels):
                shift, plate_frame_count = self.read_value(data, offset, UIntValue)
                offset += shift

                values = []
                for k in range(0, plate_frame_count):
                    shift, plate_channel_value = self.read_value(data, offset, UIntValue)
                    offset += shift
                    values.append(plate_channel_value)

                channels.append(values)

            force_plates.append(ForcePlate(plate_id, channels))
        return offset, force_plates

    def unpack_time_info(self, data):
        """
        Unpacks a TimeInfo element.

        Args:
            data: (bytes):
        Returns:
            offset: (int):
            time_info: (:class:`TimeInfo`):
        """
        offset = 0
        shift, time_code = self.read_value(data, offset, UIntValue)
        offset += shift
        shift, time_code_sub = self.read_value(data, offset, UIntValue)
        offset += shift

        # Timestamp (increased to double precision in 2.7 and later)
        shift, timestamp = self.read_value(data, offset, DoubleValue)
        offset += shift

        # Hi-res Timestamp (Version 3.0 and later)
        shift, time_camera_exposure = self.read_value(data, offset, ULongValue)
        offset += shift
        shift, time_data_received = self.read_value(data, offset, ULongValue)
        offset += shift
        shift, time_transmit = self.read_value(data, offset, ULongValue)
        offset += shift

        result = TimeInfo(timestamp, time_code, time_code_sub, time_camera_exposure, time_data_received, time_transmit)
        return offset, result

    # Unpack a marker set description packet
    def unpack_marker_set_description(self, data):
        offset = 0

        shift, name = self.read_string(data, offset)
        offset += shift
        print('Marker set Name: {}'.format(name))

        shift, marker_count = self.read_value(data, offset, IntValue)
        offset += shift

        for i in range(0, marker_count):
            shift, name = self.read_string(data, offset)
            offset += shift
            print('\tMarker Name: {}'.format(name))

        return offset

    # Unpack a rigid body description packet
    def unpack_rigid_body_description(self, data):
        offset = 0

        # Version 2.0 or higher
        shift, name = self.read_string(data, offset)
        offset += shift
        print('\tRigidBody Name: {}'.format(name))

        shift, rigid_id = self.read_value(data, offset, IntValue)
        offset += shift

        shift, parent_id = self.read_value(data, offset, IntValue)
        offset += shift

        shift, parent_translation = self.read_value(data, offset, Vector3)
        offset += shift

        # Version 3.0 and higher, rigid body marker information contained in description
        shift, marker_count = self.read_value(data, offset, UIntValue)
        offset += shift
        print('\tRigidBody Marker Count: {}'.format(marker_count))

        marker_count_range = range(0, marker_count)
        for marker in marker_count_range:
            shift, marker_offset = self.read_value(data, offset, Vector3)
            offset += shift
        for marker in marker_count_range:
            shift, active_label = self.read_value(data, offset, UIntValue)
            offset += shift

        return offset

    # Unpack a skeleton description packet
    def unpack_skeleton_description(self, data):
        offset = 0

        shift, name = self.read_string(data, offset)
        offset += shift
        print('Marker Name: {}'.format(name))

        shift, skeleton_id = self.read_value(data, offset, IntValue)
        offset += shift

        shift, rigid_body_count = self.read_value(data, offset, IntValue)
        offset += shift

        for i in range(0, rigid_body_count):
            offset += self.unpack_rigid_body_description(data[offset:])

        return offset

    def unpack_version(self, data):
        """
        Unpack Motion Server software version.

        Args:
            data (bytes):
        Returns:
            version (:class:`Version`):
        """
        offset = 256  # Skip sender Name field
        offset += 4   # Skip sender Version info
        values = struct.unpack(VERSION, data[offset:offset + 4])
        return Version(*values)

    def get_request_payload(self, command, command_string, packet_size):
        data = UShortValue.pack(command)
        data += UShortValue.pack(packet_size)
        data += command_string.encode('utf-8')
        data += b'\0'
        return data

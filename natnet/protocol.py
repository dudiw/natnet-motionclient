import struct
from collections import namedtuple
from typing import List, Tuple, NamedTuple, Dict

# Structs object types
Vector3 = struct.Struct('<fff')
Quaternion = struct.Struct('<ffff')
FloatValue = struct.Struct('<f')
DoubleValue = struct.Struct('<d')
ENDIANNESS = 'little'
VERSION = 'BBBB'

Version = namedtuple('Version', 'major, minor, build, revision')


class Position(NamedTuple):
    x: float
    y: float
    z: float


class Rotation(NamedTuple):
    w: float
    x: float
    y: float
    z: float


class LabeledMarker(NamedTuple):
    name: int
    position: Position


class MarkerSet(NamedTuple):
    name: str
    markers: List[Position]


class RigidBody(NamedTuple):
    body_id: int
    position: Position
    rotation: Rotation


class Skeleton(NamedTuple):
    skeleton_id: int
    body: Dict[int, RigidBody]


class ForcePlate(NamedTuple):
    plate_id: int
    channel: List[List[int]]


class TimeInfo(NamedTuple):
    timestamp: float
    time_code: int
    time_sub_code: int
    timestamp_camera_exposure: int
    timestamp_data_received: int
    timestamp_transmit: int


class Protocol:

    def read_int(self, data, offset):
        return int.from_bytes(data[offset:offset + 4], byteorder=ENDIANNESS)

    # Unpack a list of positions
    def unpack_positions(self, data) -> Tuple[int, List[Position]]:
        offset = 0

        # Marker count (4 bytes)
        marker_count = self.read_int(data, offset)
        offset += 4
        markers = []
        for j in range(0, marker_count):
            pos = Vector3.unpack(data[offset:offset + 12])
            offset += 12
            markers.append(Position(*pos))
        return offset, markers

    # Unpack a rigid body object from a data packet
    def _unpack_rigid_body(self, data):
        offset = 0

        # ID (4 bytes)
        body_id = self.read_int(data, offset)
        offset += 4
        print(f'ID: {body_id}')

        # Position and orientation
        pos = Vector3.unpack(data[offset:offset + 12])
        position = Position(*pos)
        offset += 12
        rot = Quaternion.unpack(data[offset:offset + 16])
        rotation = Rotation(*rot)
        offset += 16

        # Version 2 and later
        marker_error, = FloatValue.unpack(data[offset:offset + 4])
        offset += 4
        print(f'Marker Error: {marker_error}')

        # Version 2.6 and later
        param, = struct.unpack('h', data[offset:offset + 2])
        tracking_valid = (param & 0x01) != 0
        offset += 2
        print(f'Tracking Valid: {tracking_valid}')

        rigid_body = RigidBody(body_id, position, rotation)

        return offset, rigid_body

    def unpack_rigid_bodies(self, data) -> Tuple[int, List[RigidBody]]:
        offset = 0
        rigid_body_count = self.read_int(data, offset)
        offset += 4
        print(f'Rigid Body Count: {rigid_body_count}')

        rigid_bodies = []
        for i in range(0, rigid_body_count):
            shift, rigid_body = self._unpack_rigid_body(data[offset:])
            rigid_bodies.append(rigid_body)
            offset += shift

        return offset, rigid_bodies

    # Unpack a skeleton object from a data packet
    def _unpack_skeleton(self, data) -> Tuple[int, Skeleton]:
        offset = 0

        skeleton_id = self.read_int(data, offset)
        offset += 4
        print(f'ID {skeleton_id}')

        rigid_body_count = self.read_int(data, offset)
        offset += 4
        print(f'Rigid Body Count: {rigid_body_count}')

        bodies = {}
        for j in range(0, rigid_body_count):
            shift, body = self._unpack_rigid_body(data[offset:])
            bodies[body.body_id] = body
            offset += shift

        return offset, Skeleton(skeleton_id, bodies)

    def unpack_skeletons(self, data) -> Tuple[int, List[Skeleton]]:
        offset = 0
        skeleton_count = self.read_int(data, offset)
        offset += 4
        print(f'Skeleton Count: {skeleton_count}')

        skeletons = []
        for i in range(0, skeleton_count):
            shift, skeleton = self._unpack_skeleton(data[offset:])
            skeletons[skeleton.skeleton_id] = skeleton
            offset += shift

        return offset, skeletons

    def unpack_marker_sets(self, data) -> Tuple[int, List[MarkerSet]]:
        offset = 0
        marker_set_count = self.read_int(data, offset)
        offset += 4
        print(f'Marker Set Count: {marker_set_count}')

        marker_sets = []

        for i in range(0, marker_set_count):
            # Model name
            model_name, separator, remainder = bytes(data[offset:]).partition(b'\0')
            offset += len(model_name) + 1
            model_name = model_name.decode('utf-8')
            print(f'Model Name: {model_name}')

            shift, positions = self.unpack_positions(data[offset:])
            marker_sets.append(MarkerSet(model_name, positions))
            offset += shift

        return offset, marker_sets

    def unpack_labeled_markers(self, data) -> Tuple[int, List[LabeledMarker]]:
        offset = 0
        labeled_marker_count = self.read_int(data, offset)
        offset += 4
        print(f'Labeled Marker Count: {labeled_marker_count}')

        labeled_markers = []
        for i in range(0, labeled_marker_count):
            marker_id = self.read_int(data, offset)
            offset += 4
            pos = Vector3.unpack(data[offset:offset + 12])
            position = Position(*pos)
            offset += 12
            size = FloatValue.unpack(data[offset:offset + 4])
            offset += 4

            # Version 2.6 and later
            param, = struct.unpack('h', data[offset:offset + 2])
            offset += 2
            occluded = (param & 0x01) != 0
            point_cloud_solved = (param & 0x02) != 0
            model_solved = (param & 0x04) != 0

            # Version 3.0 and later
            residual, = FloatValue.unpack(data[offset:offset + 4])
            offset += 4
            print(f'Residual: {residual}')

            labeled_markers.append(LabeledMarker(marker_id, position))

        return offset, labeled_markers

    def unpack_force_plates(self, data) -> Tuple[int, List[ForcePlate]]:
        offset = 0
        plate_count = self.read_int(data, offset)
        offset += 4
        print(f'Force Plate Count: {plate_count}')
        force_plates = []
        for i in range(0, plate_count):
            # ID
            plate_id = self.read_int(data, offset)
            offset += 4
            print(f'Force Plate {i} {plate_id}')

            # Channel Count
            plate_channels = self.read_int(data, offset)
            offset += 4

            channels = []
            # Channel Data
            for j in range(0, plate_channels):
                print(f'\tChannel {j}: {plate_id}')
                plate_frame_count = self.read_int(data, offset)
                offset += 4

                values = []
                for k in range(0, plate_frame_count):
                    plate_channel_value = self.read_int(data, offset)
                    values.append(plate_channel_value)
                    offset += 4
                    print(f'\t\t {plate_channel_value}')

                channels.append(values)

            force_plates.append(ForcePlate(plate_id, channels))
        return offset, force_plates

    def unpack_time_info(self, data) -> Tuple[int, TimeInfo]:
        offset = 0
        time_code = self.read_int(data, offset)
        offset += 4
        time_code_sub = self.read_int(data, offset)
        offset += 4

        # Timestamp (increased to double precision in 2.7 and later)
        timestamp, = DoubleValue.unpack(data[offset:offset + 8])
        offset += 8

        # Hi-res Timestamp (Version 3.0 and later)
        time_camera_exposure = int.from_bytes(data[offset:offset + 8], byteorder='little')
        offset += 8
        time_data_received = int.from_bytes(data[offset:offset + 8], byteorder='little')
        offset += 8
        time_transmit = int.from_bytes(data[offset:offset + 8], byteorder='little')
        offset += 8

        result = TimeInfo(timestamp, time_code, time_code_sub, time_camera_exposure, time_data_received, time_transmit)
        return offset, result

    # Unpack a marker set description packet
    def unpack_marker_set_description(self, data):
        offset = 0

        name, separator, remainder = bytes(data[offset:]).partition(b'\0')
        offset += len(name) + 1
        print("Marker set Name:", name.decode('utf-8'))

        marker_count = self.read_int(data, offset)
        offset += 4

        for i in range(0, marker_count):
            name, separator, remainder = bytes(data[offset:]).partition(b'\0')
            offset += len(name) + 1
            print("\tMarker Name:", name.decode('utf-8'))

        return offset

    # Unpack a rigid body description packet
    def unpack_rigid_body_description(self, data):
        offset = 0

        # Version 2.0 or higher
        name, separator, remainder = bytes(data[offset:]).partition(b'\0')
        offset += len(name) + 1
        print(f'\tRigidBody Name: {name.decode("utf-8")}')

        rigid_id = self.read_int(data, offset)
        offset += 4

        parent_id = self.read_int(data, offset)
        offset += 4

        timestamp = Vector3.unpack(data[offset:offset + 12])
        offset += 12

        # Version 3.0 and higher, rigid body marker information contained in description
        marker_count = self.read_int(data, offset)
        offset += 4
        print(f'\tRigidBody Marker Count: {marker_count}')

        marker_count_range = range(0, marker_count)
        for marker in marker_count_range:
            marker_offset = Vector3.unpack(data[offset:offset + 12])
            offset += 12
        for marker in marker_count_range:
            active_label = self.read_int(data, offset)
            offset += 4

        return offset

    # Unpack a skeleton description packet
    def unpack_skeleton_description(self, data):
        offset = 0

        name, separator, remainder = bytes(data[offset:]).partition(b'\0')
        offset += len(name) + 1
        print(f'Marker Name: {name.decode("utf-8")}')

        skeleton_id = self.read_int(data, offset)
        offset += 4

        rigid_body_count = self.read_int(data, offset)
        offset += 4

        for i in range(0, rigid_body_count):
            offset += self.unpack_rigid_body_description(data[offset:])

        return offset

    def unpack_version(self, data) -> Version:
        offset = 256  # Skip sender Name field
        offset += 4   # Skip sender Version info
        values = struct.unpack(VERSION, data[offset:offset + 4])
        return Version(*values)

    def get_request_payload(self, command, command_string, packet_size):
        data = command.to_bytes(2, byteorder='little')
        data += packet_size.to_bytes(2, byteorder='little')

        data += command_string.encode('utf-8')
        data += b'\0'
        return data

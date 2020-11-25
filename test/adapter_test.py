import os
from typing import List

from natnet.adapter import Adapter, MotionListener
from natnet.protocol import RigidBody, Skeleton, TimeInfo

PATH_DATA = 'data'

PATH_FRAME = 'frame_packet_v3.bin'
PATH_VERSION = 'version_packet_v3.bin'


class TestListener(MotionListener):
    """
    A class of callback functions that are invoked with information from NatNet server.
    """
    def __init__(self):
        super().__init__()

    def on_version(self, version):
        print(f'Version {version}')

    def on_rigid_body(self, bodies: List[RigidBody], time_info: TimeInfo):
        print(f'RigidBodies {bodies}')

    def on_skeletons(self, skeletons: List[Skeleton], time_info: TimeInfo):
        print(f'Skeletons {skeletons}')

    def on_labeled_markers(self, markers, time_info: TimeInfo):
        print(f'Labeled marker {markers}')

    def on_unlabeled_marker(self, marker):
        print(f'Unlabeled marker {marker}')


if __name__ == "__main__":
    listener = TestListener()
    adapter = Adapter(listener)

    # Test frame payload
    frame = open(os.path.join(PATH_DATA, PATH_FRAME), 'rb').read()
    adapter.process_message(frame)

    # Test version payload
    version = open(os.path.join(PATH_DATA, PATH_VERSION), 'rb').read()
    adapter.process_message(version)


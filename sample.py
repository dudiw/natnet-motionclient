import time
from typing import List

from natnet.adapter import MotionListener
from natnet.protocol import RigidBody, Skeleton, TimeInfo
from natnet.motion_client import MotionClient


class Listener(MotionListener):
    """
    A class of callback functions that are invoked with information from NatNet server.
    """
    def __init__(self):
        super().__init__()

    def on_version(self, version):
        print(f'Version {version}')

    def on_rigid_body(self, bodies: List[RigidBody], time_info: TimeInfo):
        print(f'Rigid body {bodies}')

    def on_skeletons(self, skeletons: List[Skeleton], time_info: TimeInfo):
        print(f'Labeled marker {skeletons}')

    def on_labeled_markers(self, markers, time_info: TimeInfo):
        print(f'Labeled marker {markers}')

    def on_unlabeled_marker(self, marker):
        print(f'Unlabeled marker {marker}')


if __name__ == "__main__":
    # Create listener
    listener = Listener()

    # Create a NatNet client
    client = MotionClient(listener)

    # Data of rigid bodies and markers delivered via listener on a separate thread
    client.get_data()

    # Read version (optional)
    client.get_version()

    # The client continuously reads data until client.stop() is called
    time.sleep(5)

    # Stops data stream and disconnects the client
    client.disconnect()

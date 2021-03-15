import time

from natnet import MotionListener, MotionClient


class Listener(MotionListener):
    """
    A class of callback functions that are invoked with information from NatNet server.
    """
    def __init__(self):
        super(Listener, self).__init__()

    def on_version(self, version):
        print('Version {}'.format(version))

    def on_rigid_body(self, bodies, time_info):
        print('RigidBodies {}'.format(bodies))

    def on_skeletons(self, skeletons, time_info):
        print('Skeletons {}'.format(skeletons))

    def on_labeled_markers(self, markers, time_info):
        print('Labeled marker {}'.format(markers))

    def on_unlabeled_markers(self, markers, time_info):
        print('Unlabeled marker {}'.format(markers))


if __name__ == '__main__':
    # Create listener
    listener = Listener()

    # Create a NatNet client with IP address of your local network interface
    client = MotionClient(listener, ip_local='127.0.0.1')

    # Data of rigid bodies and markers delivered via listener on a separate thread
    client.get_data()

    # Read version (optional)
    client.get_version()

    # The client continuously reads data until client.disconnect() is called
    time.sleep(5)

    # Stops data stream and disconnects the client
    client.disconnect()

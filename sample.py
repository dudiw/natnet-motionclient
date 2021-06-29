import time

from natnet import MotionListener, MotionClient


class Listener(MotionListener):
    """
    A class containing callback functions that are invoked upon information from NatNet server.
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

    def on_rigid_body_descriptors(self, descriptors):
        print('RigidBody Descriptors {}'.format(descriptors))


if __name__ == '__main__':
    # Create listener
    listener = Listener()

    # Create a NatNet client with IP address of your local network interface
    client = MotionClient(listener, ip_local='132.68.51.42', ip_multicast='239.255.42.99', ip_server='132.68.37.110')

    # Data of rigid bodies and markers delivered via listener on a separate thread
    client.get_data()

    # Read rigid body descriptors (optional)
    client.get_descriptors()

    # Read version (optional)
    client.get_version()

    # The client continuously reads data until client.disconnect() is called
    try:
        time.sleep(5)
    except KeyboardInterrupt as e:
        pass

    # Stops data stream and disconnects the client
    client.disconnect()
    print('post disconnect')

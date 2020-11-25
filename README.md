# Overview
#### NatNet MotionClient
A Python NatNat client for motion tracking with [OptiTrack NatNetSDK](https://optitrack.com/software/natnet-sdk/) v3.1.0 (Motive v2.1).

Stream live motion capture (rigid bodies, markers, skeletons, etc) over a network.

-----

#### Features
- Python +2.7 compatible
- No 3rd party library dependencies

-----

#### Usage
First, implement (or inherit) the `MotionListener` class to receive callbacks once motion information becomes available:
```python
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
```

Then instantiate `MotionClient` and request data frames.
Updates are delivered on a separate thread continuously until `MotionClient.disconect()` is called.
```python
    # Create listener
    listener = Listener()

    # Create a NatNet client
    client = MotionClient(listener)

    # Data of rigid bodies and markers delivered via listener on a separate thread
    client.get_data()

    # Read version (optional)
    client.get_version()

    # The client continuously reads data until client.disconnect() is called
    time.sleep(5)

    # Stops data stream and disconnects the client
    client.disconnect()
```

See `sample.py` for a full example (requires NatNet server / Motive).
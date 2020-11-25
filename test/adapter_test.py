import os

from natnet import MotionListener
from natnet.adapter import Adapter

PATH_DATA = 'data'

PATH_FRAME = 'frame_packet_v3.bin'
PATH_VERSION = 'version_packet_v3.bin'
PATH_MODEL = 'model_def_packet_v3.bin'


class TestListener(MotionListener):
    """
    A class of callback functions that are invoked with information from NatNet server.
    """
    def __init__(self):
        super(TestListener, self).__init__()

    def on_version(self, version):
        print('{}'.format(version))

    def on_rigid_body(self, rigid_bodies, time_info):
        print('RigidBody Count {}'.format(len(rigid_bodies)))
        for body in rigid_bodies:
            print('\t{}: {}'.format(body.body_id, body))
        print('Time: {}'.format(time_info.timestamp))

    def on_skeletons(self, skeletons, time_info):
        print('Skeleton Count {}'.format(len(skeletons)))
        for skeleton in skeletons:
            print('\t{}: {}'.format(skeleton.skeleton_id, skeleton))
        print('Time: {}'.format(time_info.timestamp))

    def on_labeled_markers(self, markers, time_info):
        print('Labeled marker Count {}'.format(len(markers)))
        for marker in markers:
            print('\t{}: {}'.format(marker.name, marker))
        print('Time: {}'.format(time_info.timestamp))

    def on_unlabeled_markers(self, markers, time_info):
        print('Unlabeled marker Count {}'.format(len(markers)))
        for marker in markers:
            print('\t{}'.format(marker))
        print('Time: {}'.format(time_info.timestamp))


if __name__ == '__main__':
    listener = TestListener()
    adapter = Adapter(listener)

    # Test frame payload
    frame = open(os.path.join(PATH_DATA, PATH_FRAME), 'rb').read()
    adapter.process_message(frame)

    # Test version payload
    version = open(os.path.join(PATH_DATA, PATH_VERSION), 'rb').read()
    adapter.process_message(version)

    # Test model definitions payload
    models = open(os.path.join(PATH_DATA, PATH_MODEL), 'rb').read()
    adapter.process_message(models)

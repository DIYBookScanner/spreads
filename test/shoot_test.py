import os
from itertools import chain, repeat

from nose.tools import raises
from mock import call, MagicMock as Mock, patch

import spreads.commands as cmd
#from spreads import config


class TestConfigure(object):
    def setUp(self):
        pass
#        config.clear()
#        config.read(user=False)

    def test_configure(self):
        cams = [Mock(), Mock()]
        for cam in cams:
            cam.orientation = None
            cam.set_orientation = Mock()
        cmd.detect_cameras = Mock(side_effect=[[cams[0]], [cams[1]]])
        cmd.getch = Mock(return_value=' ')
        cmd.configure()
        assert cams[0].set_orientation.call_args == call('left')
        assert cams[1].set_orientation.call_args == call('right')

    @raises(SystemExit)
    def test_configure_nocamera(self):
        cmd.detect_cameras = Mock(return_value=[])
        cmd.getch = Mock(return_value=' ')
        cmd.configure()


class TestShoot(object):
    def setUp(self):
        pass
        #config.clear()
        #config.read(user=False)

    def test_shoot(self):
        cams = [Mock(), Mock()]
        cams[0].orientation = 'left'
        cams[1].orientation = 'right'
        cmd.detect_cameras = Mock(return_value=cams)
        cmd.getch = Mock(side_effect=chain(' ', repeat('b', 8), 'c'))
        cmd.run_parallel = Mock()
        cmd.find_in_path = Mock(return_value=True)
        cmd.shoot(iso_value=100, shutter_speed=0.5, zoom_value=4)
        for cam in cams:
            # 1 for setup, 8 for shooting
            assert cmd.getch.call_count == 10
            assert cmd.run_parallel.call_count == 9
            supposed_calls = repeat(call([{'func': x.shoot,
                                           'kwargs': {'iso_value': 100,
                                                      'shutter_speed': 0.5}}
                                          for x in cams]),
                                    8)
            for supposed_call, real_call in (zip(cmd.run_parallel
                                                 .call_args_list[1:],
                                                 supposed_calls)):
                assert supposed_call == real_call

    @raises(SystemExit)
    def test_shoot_nocams(self):
        cmd.getch = Mock(return_value='b')
        cmd.detect_cameras = Mock(return_value=[])
        cmd.shoot(cameras=[])

    @raises(SystemExit)
    def test_shoot_noorientation(self):
        cams = [Mock(), Mock()]
        for cam in cams:
            cam.orientation = None
        cmd.detect_cameras = Mock(return_value=cams)
        cmd.getch = Mock(side_effect=[' ', ' '])
        cmd.find_in_path = Mock(return_value=True)
        cmd.shoot(iso_value=100, shutter_speed=0.5, zoom_value=4)


class TestDownload(object):
    def setUp(self):
        #config.clear()
        #config.read(user=False)
        cams = [Mock(), Mock()]
        cams[0].orientation = 'left'
        cams[1].orientation = 'right'
        cmd.detect_cameras = Mock(return_value=cams)
        cmd.run_parallel = Mock()
        cmd.shutil.rmtree = Mock()
        cmd.shutil.copyfile = Mock()

    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_download(self, listdir, exists, mkdir):
        exists.return_value = False
        listdir.return_value = ['1.jpg', '2.jpg', '3.jpg']
        cmd.os.mkdir = mkdir
        cmd.os.path.exists = exists
        cmd.os.listdir = listdir
        cmd.download('/tmp/foo')
        # TODO: Path is created?
        # TODO: Files are downloaded?
        # TODO: Files are deleted?
        # TODO: Files are combined?
        # TODO: Single directories are deleted?


@patch('os.path.exists')
@patch('os.mkdir')
class TestPostProcess(object):
    def setUp(self):
        cmd.run_multicore = Mock()
        cmd.subprocess.call = Mock()


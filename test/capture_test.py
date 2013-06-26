import os
from itertools import chain, repeat

from nose.tools import raises
from mock import call, MagicMock as Mock, patch

import spreads.commands as cmd
from spreads import config
from spreads.util import SpreadsException, DeviceException


class TestConfigure(object):
    def setUp(self):
        config.clear()
        config.read(user=False)

    def test_configure(self):
        cams = [Mock(), Mock()]
        for cam in cams:
            cam.orientation = None
            cam.set_orientation = Mock()
        cmd.get_devices = Mock(side_effect=[[cams[0]], [cams[1]]])
        cmd.getch = Mock(return_value=' ')
        cmd.configure()
        assert cams[0].set_orientation.call_args == call('left')
        assert cams[1].set_orientation.call_args == call('right')

    @raises(DeviceException)
    def test_configure_nodevice(self):
        cmd.get_devices = Mock(return_value=[])
        cmd.getch = Mock(return_value=' ')
        cmd.configure()


class TestCapture(object):
    def setUp(self):
        config.clear()
        config.read(user=False)

    def test_capture(self):
        cams = [Mock(), Mock()]
        cams[0].orientation = 'left'
        cams[1].orientation = 'right'
        cmd.get_devices = Mock(return_value=cams)
        cmd.getch = Mock(side_effect=chain(' ', repeat('b', 8), 'c'))
        cmd.run_parallel = Mock()
        cmd.find_in_path = Mock(return_value=True)
        cmd.capture()
        for cam in cams:
            # 1 for setup, 8 for captureing
            assert cmd.getch.call_count == 10
            assert cmd.run_parallel.call_count == 9
            supposed_calls = repeat(call([{'func': x.capture} for x in cams]),
                                    8)
            for supposed_call, real_call in (zip(cmd.run_parallel
                                                 .call_args_list[1:],
                                                 supposed_calls)):
                assert supposed_call == real_call

    @raises(DeviceException)
    def test_capture_nocams(self):
        cmd.getch = Mock(return_value='b')
        cmd.get_devices = Mock(return_value=[])
        cmd.capture(devices=[])

    @raises(DeviceException)
    def test_capture_noorientation(self):
        cams = [Mock(), Mock()]
        for cam in cams:
            cam.orientation = None
        cmd.get_devices = Mock(return_value=cams)
        cmd.getch = Mock(side_effect=[' ', ' '])
        cmd.find_in_path = Mock(return_value=True)
        cmd.capture()


class TestDownload(object):
    def setUp(self):
        config.clear()
        config.read(user=False)
        cams = [Mock(), Mock()]
        cams[0].orientation = 'left'
        cams[1].orientation = 'right'
        cmd.get_devices = Mock(return_value=cams)
        cmd.run_parallel = Mock()
        mock_plugin = Mock()
        mock_plugin.config_key = 'combine'
        cmd.get_plugins = Mock(return_value=[mock_plugin])

    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_download(self, listdir, exists, mkdir):
        exists.return_value = False
        listdir.return_value = ['1.jpg', '2.jpg', '3.jpg']
        cmd.os.mkdir = mkdir
        cmd.os.path.exists = exists
        cmd.os.listdir = listdir
        cmd.download(args=Mock(), path='/tmp/foo')
        # TODO: Path is created?
        # TODO: Files are downloaded?
        # TODO: Files are deleted?
        # TODO: Files are combined?
        # TODO: Single directories are deleted?

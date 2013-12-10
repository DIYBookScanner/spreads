from mock import call, MagicMock as Mock, patch
from nose.tools import raises

import spreads
import spreads.workflow as flow

spreads.util.find_in_path = Mock(return_value=True)


class TestCapture(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        spreads.config['parallel_capture'] = True
        self.cams = [Mock(), Mock()]
        self.cams[0].orientation = 'left'
        self.cams[0].orientation = 'right'
        self.plugins = [Mock(), Mock()]
        flow.get_pluginmanager = Mock(return_value=self.plugins)
        flow.time = Mock()

    def test_prepare_capture(self):
        flow.prepare_capture(self.cams, '/tmp/foo')
        for cam in self.cams:
            assert cam.prepare_capture.call_count == 1
        for plug in self.plugins:
            assert plug.obj.prepare_capture.call_count == 1
            assert plug.obj.prepare_capture.call_args_list == (
                [call(self.cams, '/tmp/foo')])

    def test_capture(self):
        flow.capture(self.cams, '/tmp/foo')
        for cam in self.cams:
            assert cam.capture.call_count == 1
        for plug in self.plugins:
            assert plug.obj.capture.call_count == 1
            assert plug.obj.capture.call_args_list == [call(self.cams, '/tmp/foo')]

    def test_capture_noparallel(self):
        spreads.config['parallel_capture'] = False
        flow.capture(self.cams, '/tmp/foo')
        # TODO: Find a way to verify that the cameras were indeed triggered
        #       in sequence and not in parallel
        for cam in self.cams:
            assert cam.capture.call_count == 1

    def test_finish_capture(self):
        flow.finish_capture(self.cams, '/tmp/foo')
        for plug in self.plugins:
            assert plug.obj.finish_capture.call_count == 1
            assert plug.obj.finish_capture.call_args_list == (
                [call(self.cams, '/tmp/foo')])
    #@raises(DeviceException)
    #def test_capture_nocams(self):
    #    cmd.getch = Mock(return_value='b')
    #    cmd.get_devices = Mock(return_value=[])
    #    cmd.capture(devices=[])

    #@raises(DeviceException)
    #def test_capture_noorientation(self):
    #    cams = [Mock(), Mock()]
    #    for cam in cams:
    #        cam.orientation = None
    #    cmd.get_devices = Mock(return_value=cams)
    #    cmd.getch = Mock(side_effect=[' ', ' '])
    #    cmd.find_in_path = Mock(return_value=True)
    #    cmd.capture()


class TestProcess(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        self.plugins = [Mock(), Mock()]
        flow.get_pluginmanager = Mock(return_value=self.plugins)

    @patch('shutil.copytree')
    def test_process(self, shutil):
        flow.shutil = shutil
        flow.process('/tmp/foo')
        for plug in self.plugins:
            assert plug.obj.process.call_count == 1
            assert plug.obj.process.call_args_list == [call('/tmp/foo')]

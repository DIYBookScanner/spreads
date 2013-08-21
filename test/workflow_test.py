from mock import call, MagicMock as Mock, patch

import spreads
import spreads.workflow as flow

spreads.util.find_in_path = Mock(return_value=True)


class TestCapture(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        self.cams = [Mock(), Mock()]
        self.cams[0].orientation = 'left'
        self.cams[0].orientation = 'right'
        self.plugins = [Mock(), Mock()]
        flow.get_pluginmanager = Mock(return_value=self.plugins)
        flow.time = Mock()

    def test_prepare_capture(self):
        flow.prepare_capture(self.cams)
        for cam in self.cams:
            assert cam.prepare_capture.call_count == 1
        for plug in self.plugins:
            assert plug.obj.prepare_capture.call_count == 1
            assert plug.obj.prepare_capture.call_args_list == (
                [call(self.cams)])

    def test_capture(self):
        flow.capture(self.cams)
        for cam in self.cams:
            assert cam.capture.call_count == 1
        for plug in self.plugins:
            assert plug.obj.capture.call_count == 1
            assert plug.obj.capture.call_args_list == [call(self.cams)]

    def test_finish_capture(self):
        flow.finish_capture(self.cams)
        for plug in self.plugins:
            assert plug.obj.finish_capture.call_count == 1
            assert plug.obj.finish_capture.call_args_list == (
                [call(self.cams)])
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


class TestDownload(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        self.cams = [Mock(), Mock()]
        self.cams[0].orientation = 'left'
        self.cams[1].orientation = 'right'
        self.plugins = [Mock(), Mock()]
        flow.get_pluginmanager = Mock(return_value=self.plugins)

    @patch('os.mkdir')
    @patch('os.path.exists')
    def test_download(self, exists, mkdir):
        spreads.config['keep'] = False
        exists.return_value = False
        flow.os.mkdir = mkdir
        flow.os.path.exists = exists
        flow.download(devices=self.cams, path='/tmp/foo')
        assert flow.os.mkdir.call_count == 3
        assert call('/tmp/foo') in flow.os.mkdir.call_args_list
        assert call('/tmp/foo/right') in flow.os.mkdir.call_args_list
        assert call('/tmp/foo/left') in flow.os.mkdir.call_args_list
        for cam in self.cams:
            assert cam.download_files.call_count == 1
            assert cam.download_files.call_args_list == [call('/tmp/foo/{0}'
                .format(cam.orientation.lower()))]
            assert cam.delete_files.call_count == 1
        for plug in self.plugins:
            assert plug.obj.download.call_count == 1
            assert plug.obj.download.call_args_list == [call(
                self.cams, '/tmp/foo')]
            assert plug.obj.delete.call_count == 1
            assert plug.obj.delete.call_args_list == [call(self.cams)]


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

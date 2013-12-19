from mock import call, MagicMock as Mock, patch, DEFAULT
from nose.tools import raises

import spreads.confit as confit
import spreads.util as util
import spreads.workflow as workflow

util.find_in_path = Mock(return_value=True)


class TestWorkflow(object):
    def setUp(self):
        self.plugins = [Mock() for x in xrange(3)]
        self.devices = [Mock() for x in xrange(2)]
        self.devices[0].target_page = 'odd'
        self.devices[1].target_page = 'even'
        workflow.get_pluginmanager = Mock(return_value=self.plugins)
        workflow.get_devices = Mock(return_value=self.devices)
        config = confit.Configuration('test_workflow')
        self.workflow = workflow.Workflow(config=config,
                                          path='/tmp/test_workflow')

    def test_get_plugins(self):
        foo = self.workflow.plugins
        bar = self.workflow.plugins
        assert workflow.get_pluginmanager.call_count == 1
        assert foo == bar == [x.obj for x in self.plugins]

    def test_get_devices(self):
        foo = self.workflow.devices
        bar = self.workflow.devices
        assert workflow.get_devices.call_count == 1
        assert foo == bar == self.devices

    @raises(util.DeviceException)
    def test_get_devices_no_device(self):
        workflow.get_devices = Mock(return_value=[])
        self.workflow.devices

    @patch('spreads.plugin.os.mkdir')
    def test_get_next_filename(self, mkdir):
        fname = self.workflow._get_next_filename('jpg', target_page='odd')
        assert fname == '/tmp/test_workflow/raw/001.jpg'
        fname = self.workflow._get_next_filename('jpg', target_page='even')
        assert fname == '/tmp/test_workflow/raw/000.jpg'
        self.workflow._pages_shot += 2
        fname = self.workflow._get_next_filename('jpg', target_page='odd')
        assert fname == '/tmp/test_workflow/raw/003.jpg'
        fname = self.workflow._get_next_filename('jpg', target_page='even')
        assert fname == '/tmp/test_workflow/raw/002.jpg'

    def test_prepare_capture(self):
        self.workflow.prepare_capture()
        for dev in self.devices:
            assert dev.prepare_capture.call_count == 1
            assert dev.prepare_capture.called_with(call('/tmp/test_workflow'))
        for plug in self.plugins:
            assert plug.obj.prepare_capture.call_count == 1
            assert plug.obj.prepare_capture.call_args_list == (
                [call(self.devices, '/tmp/test_workflow')])

    def test_capture(self):
        self.workflow.config['parallel_capture'] = True
        self.workflow.config['flip_target_pages'] = False
        self.workflow.capture()
        self.devices[0].capture.assert_called_with(
            '/tmp/test_workflow/raw/001.jpg')
        self.devices[1].capture.assert_called_with(
            '/tmp/test_workflow/raw/000.jpg')
        for plug in self.plugins:
            assert plug.obj.capture.call_count == 1
            assert (plug.obj.capture.call_args_list ==
                    [call(self.devices, '/tmp/test_workflow')])

    def test_capture_noparallel(self):
        self.workflow.config['parallel_capture'] = False
        self.workflow.config['flip_target_pages'] = False
        self.workflow.capture()
        # TODO: Find a way to verify that the cameras were indeed triggered
        #       in sequence and not in parallel
        for dev in self.devices:
            assert dev.capture.call_count == 1

    def test_capture_flip_target_pages(self):
        self.workflow.config['parallel_capture'] = False
        self.workflow.config['flip_target_pages'] = True
        self.workflow.capture()
        self.devices[0].capture.assert_called_with(
            '/tmp/test_workflow/raw/000.jpg')
        self.devices[1].capture.assert_called_with(
            '/tmp/test_workflow/raw/001.jpg')

    def test_finish_capture(self):
        self.workflow.finish_capture()
        for plug in self.plugins:
            assert plug.obj.finish_capture.call_count == 1
            assert plug.obj.finish_capture.call_args_list == (
                [call(self.devices, '/tmp/test_workflow')])

    def test_process(self):
        self.workflow.process()
        for plug in self.plugins:
            assert plug.obj.process.call_count == 1
            assert (plug.obj.process.call_args_list ==
                    [call('/tmp/test_workflow')])

    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_output(self, exists, mkdir):
        exists.return_value = False
        self.workflow.output()
        for plug in self.plugins:
            assert plug.obj.output.call_count == 1
            assert (plug.obj.output.call_args_list ==
                    [call('/tmp/test_workflow')])
        assert mkdir.call_count == 1
        assert call('/tmp/test_workflow/out') in mkdir.call_args_list

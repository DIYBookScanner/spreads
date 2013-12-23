from __future__ import division, unicode_literals

import unittest

import pytest
from mock import call, MagicMock as Mock, patch, DEFAULT
from spreads.vendor.pathlib import Path

import spreads.confit as confit
import spreads.util as util
import spreads.workflow as workflow

util.find_in_path = Mock(return_value=True)


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.plugins = [Mock() for x in xrange(3)]
        self.devices = [Mock() for x in xrange(2)]
        self.devices[0].target_page = 'odd'
        self.devices[1].target_page = 'even'
        workflow.get_pluginmanager = Mock(return_value=self.plugins)
        workflow.get_devices = Mock(return_value=self.devices)
        config = confit.Configuration('test_workflow')
        self.mock_path = Mock(wraps=Path('/tmp/test_workflow'), spec=Path)
        self.workflow = workflow.Workflow(config=config,
                                          path=self.mock_path)

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

    def test_get_devices_no_device(self):
        workflow.get_devices = Mock(return_value=[])
        with pytest.raises(util.DeviceException) as excinfo:
            self.workflow.devices

    @patch('spreads.plugin.os.mkdir')
    def test_get_next_filename(self, mkdir):
        fname = self.workflow._get_next_filename('jpg', target_page='odd')
        assert fname == self.mock_path/'raw'/'001.jpg'
        fname = self.workflow._get_next_filename('jpg', target_page='even')
        assert fname == self.mock_path/'raw'/'000.jpg'
        self.workflow._pages_shot += 2
        fname = self.workflow._get_next_filename('jpg', target_page='odd')
        assert fname == self.mock_path/'raw'/'003.jpg'
        fname = self.workflow._get_next_filename('jpg', target_page='even')
        assert fname == self.mock_path/'raw'/'002.jpg'

    def test_prepare_capture(self):
        self.workflow.prepare_capture()
        for dev in self.devices:
            assert dev.prepare_capture.call_count == 1
            assert dev.prepare_capture.called_with(self.mock_path)
        for plug in self.plugins:
            assert plug.obj.prepare_capture.call_count == 1
            assert plug.obj.prepare_capture.call_args_list == (
                [call(self.devices, self.mock_path)])

    def test_capture(self):
        self.workflow.config['device']['parallel_capture'] = True
        self.workflow.config['device']['flip_target_pages'] = False
        self.workflow.capture()
        self.devices[0].capture.assert_called_with(self.mock_path/'raw'/'001.jpg')
        self.devices[1].capture.assert_called_with(self.mock_path/'raw'/'000.jpg')
        for plug in self.plugins:
            assert plug.obj.capture.call_count == 1
            assert (plug.obj.capture.call_args_list ==
                    [call(self.devices, self.mock_path)])

    def test_capture_noparallel(self):
        self.workflow.config['device']['parallel_capture'] = False
        self.workflow.config['device']['flip_target_pages'] = False
        self.workflow.capture()
        # TODO: Find a way to verify that the cameras were indeed triggered
        #       in sequence and not in parallel
        for dev in self.devices:
            assert dev.capture.call_count == 1

    def test_capture_flip_target_pages(self):
        self.workflow.config['device']['parallel_capture'] = False
        self.workflow.config['device']['flip_target_pages'] = True
        self.workflow.capture()
        self.devices[0].capture.assert_called_with(self.mock_path/'raw'/'000.jpg')
        self.devices[1].capture.assert_called_with(self.mock_path/'raw'/'001.jpg')

    def test_finish_capture(self):
        self.workflow.finish_capture()
        for plug in self.plugins:
            assert plug.obj.finish_capture.call_count == 1
            assert plug.obj.finish_capture.call_args_list == (
                [call(self.devices, self.mock_path)])

    def test_process(self):
        self.workflow.process()
        for plug in self.plugins:
            assert plug.obj.process.call_count == 1
            assert (plug.obj.process.call_args_list ==
                    [call(self.mock_path)])

    def test_output(self):
        (self.mock_path/'out').exists.return_value = False
        self.workflow.output()
        for plug in self.plugins:
            assert plug.obj.output.call_count == 1
            assert (plug.obj.output.call_args_list ==
                    [call(self.mock_path)])
        assert (self.mock_path/'out').mkdir.call_count == 1

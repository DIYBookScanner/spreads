import time
import unittest
from itertools import chain, repeat

import pytest
import spreads.vendor.confit as confit
from mock import patch, MagicMock as Mock

import spreads
import spreads.cli as cli
from spreads.util import DeviceException

spreads.util.find_in_path = Mock(return_value=True)


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.workflow = Mock()
        self.workflow.devices = [Mock(), Mock()]
        self.workflow.devices[0].target_page = 'even'
        self.workflow.devices[1].target_page = 'odd'
        self.workflow.capture_start = time.time()
        self.workflow.config = confit.Configuration('test_cli')
        cli.Workflow = Mock(return_value=self.workflow)

    def test_capture(self):
        self.workflow.config['capture']['capture_keys'] = ["b", " "]
        cli.getch = Mock(side_effect=chain(repeat('b', 3), 'f'))
        cli.capture(self.workflow)
        assert cli.getch.call_count == 4
        assert self.workflow.prepare_capture.call_count == 1
        assert self.workflow.capture.call_count == 3
        assert self.workflow.finish_capture.call_count == 1
        #TODO: stats correct?

    def test_capture_nodevices(self):
        cli.getch = Mock(return_value=' ')
        self.workflow.devices = []
        with pytest.raises(DeviceException) as excinfo:
            cli.capture(self.workflow)

    def test_capture_no_target_page(self):
        self.workflow.devices[0].target_page = None
        cli.getch = Mock(return_value='c')
        with pytest.raises(DeviceException) as excinfo:
            cli.capture(self.workflow)

    def test_postprocess(self):
        self.workflow.path = '/tmp/foo'
        cli.postprocess(self.workflow)
        assert self.workflow.process.call_count == 1

    @patch('spreads.cli.capture')
    @patch('spreads.cli.postprocess')
    @patch('spreads.cli.output')
    def test_wizard(self, capture, postprocess, output):
        self.workflow.config['path'] = '/tmp/foo'
        cli.wizard(self.workflow.config)
        capture.assert_called_with(self.workflow.config)
        postprocess.assert_called_with(self.workflow.config)
        output.assert_called_with(self.workflow.config)


    def test_parser(self):
        cli.get_pluginmanager = Mock()
        # TODO: Test if plugin arguments are added
        parser = cli.setup_parser()

    @patch('os.path.exists')
    def test_main(self, exists):
        # TODO: Config dumped?
        # TODO: Config from args?
        # TODO: Loglevel set correctly?
        # TODO: Correct function executed?
        self.workflow.config["loglevel"] = "info"
        self.workflow.config["verbose"] = False
        self.workflow.config.dump = Mock()
        cli.confit.LazyConfig = Mock(return_value=self.workflow.config)
        cli.test_cmd = Mock()
        cli.setup_plugin_config = Mock()
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.verbose = False
        mock_args.subcommand = Mock()
        mock_parser.parse_args = Mock(return_value=mock_args)
        cli.setup_parser = Mock(return_value=mock_parser)
        cli.set_config_from_args = Mock()
        exists.return_value = False
        cli.os.path.exists = exists
        cli.main()
        assert mock_args.subcommand.call_count == 1

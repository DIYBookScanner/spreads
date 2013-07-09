from itertools import chain, repeat

from mock import call, patch, MagicMock as Mock
from nose.tools import raises

import spreads
import spreads.cli as cli
from spreads.util import DeviceException


class TestCLI(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        self.plugins = [Mock(), Mock()]
        cli.get_pluginmanager = Mock(return_value=self.plugins)
        cli.workflow = Mock()
        self.devices = [Mock(), Mock()]

    def test_configure(self):
        cli.getch = Mock(return_value=' ')
        cli.get_devices = Mock(side_effect=[[x] for x in self.devices])
        cli.configure()
        assert cli.getch.call_count == 4
        assert cli.get_devices.call_count == 2
        assert self.devices[0].set_orientation.call_count == 1
        assert self.devices[0].set_orientation.call_args_list == [call('left')]
        assert self.devices[1].set_orientation.call_count == 1
        assert self.devices[1].set_orientation.call_args_list == (
            [call('right')])

    @raises(DeviceException)
    def test_configure_twodevices(self):
        cli.getch = Mock(return_value=' ')
        cli.get_devices = Mock(return_value=self.devices)
        cli.configure()

    @raises(DeviceException)
    def test_configure_nodevices(self):
        cli.getch = Mock(return_value=' ')
        cli.get_devices = Mock(return_value=[])
        cli.configure()

    def test_capture(self):
        cli.getch = Mock(side_effect=chain(repeat('b', 3), 'c'))
        cli.get_devices = Mock(return_value=self.devices)
        cli.capture()
        assert cli.getch.call_count == 4
        assert cli.workflow.prepare_capture.call_count == 1
        assert cli.workflow.capture.call_count == 2
        assert cli.workflow.finish_capture.call_count == 1
        #TODO: stats correct?

    @raises(DeviceException)
    def test_capture_nodevices(self):
        cli.getch = Mock(return_value=' ')
        cli.get_devices = Mock(return_value=[])
        cli.capture()

    @raises(DeviceException)
    def test_capture_noorientation(self):
        self.devices[0].orientation = None
        cli.getch = Mock(return_value='c')
        cli.get_devices = Mock(return_value=self.devices)
        cli.capture()

    def test_download(self):
        args = Mock()
        args.path = '/tmp/foo'
        cli.get_devices = Mock(return_value=self.devices)
        cli.download(args=args)
        assert cli.workflow.download.call_args == call(self.devices,
                                                       '/tmp/foo')

    def test_postprocess(self):
        args = Mock()
        args.path = '/tmp/foo'
        cli.postprocess(args=args)
        assert cli.workflow.process.call_args == call('/tmp/foo')

    def test_wizard(self):
        args = Mock()
        args.path = '/tmp/foo'
        self.devices[0].orientation = None
        cli.getch = Mock(return_value=' ')
        cli.get_devices = Mock(return_value=self.devices)
        cli.configure = Mock(side_effect=(DeviceException('boom'),
                                          True))
        cli.capture = Mock()
        cli.download = Mock()
        cli.postprocess = Mock()
        cli.wizard(args)
        assert cli.getch.call_count == 1
        assert cli.get_devices.call_count == 1
        assert cli.configure.call_count == 2
        assert cli.capture.call_args == call(devices=self.devices)
        assert cli.download.call_args == call(path='/tmp/foo')
        assert cli.postprocess.call_args == call(path='/tmp/foo')

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
        cli.setup_parser = Mock()
        cli.config.dump = Mock()
        exists.return_value = False
        cli.os.path.exists = exists
        cli.main()


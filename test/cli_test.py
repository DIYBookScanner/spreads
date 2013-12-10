from itertools import chain, repeat

from mock import call, patch, MagicMock as Mock
from nose.tools import raises

import spreads
import spreads.cli as cli
from spreads.util import DeviceException

spreads.util.find_in_path = Mock(return_value=True)


class TestCLI(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []
        self.plugins = [Mock(), Mock()]
        cli.get_pluginmanager = Mock(return_value=self.plugins)
        cli.workflow = Mock()
        self.devices = [Mock(), Mock()]
        self.devices[0].orientation = 'right'
        self.devices[1].orientation = 'left'

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
        assert cli.workflow.capture.call_count == 3
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

    def test_postprocess(self):
        args = Mock()
        args.path = '/tmp/foo'
        cli.postprocess(args=args)
        assert cli.workflow.process.call_args == call('/tmp/foo')

    def test_wizard(self):
        args = Mock()
        args.path = '/tmp/foo'
        cli.getch = Mock(side_effect=chain(repeat('b', 10), 'c',
                                           repeat('b', 10)))
        cli.get_devices = Mock(side_effect=self.devices)
        spreads.config['keep'] = False
        cli.wizard(args, self.devices)

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

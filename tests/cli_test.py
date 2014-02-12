from itertools import chain, repeat

import pytest
from mock import Mock, patch

import spreads.cli as cli
from spreads.util import DeviceException


@pytest.yield_fixture
def mock_input():
    with patch('__builtin__.raw_input') as mock_input:
        yield mock_input


@pytest.yield_fixture
def mock_getch():
    with patch('spreads.cli.getch') as getch:
        yield getch


@pytest.yield_fixture
def mock_pkg_resources():
    with patch('spreads.cli.pkg_resources') as pkg:
        yield pkg


@patch('spreads.cli.sys.stdin')
@patch('spreads.cli.termios')
@patch('spreads.cli.tty')
def test_getch(tty, termios, stdin):
    stdin.fileno.return_value = 1
    stdin.read.return_value = 'b'
    termios.tcgetattr.return_value = 16
    assert cli.getch() == 'b'
    termios.tcsetattr.assert_called_once_with(1, termios.TCSADRAIN, 16)


def test_select_driver(mock_pkg_resources, mock_input):
    driver = Mock()
    driver.name = "testdriver"
    mock_pkg_resources.iter_entry_points.return_value = (driver, )
    mock_input.side_effect = ('a', '1')
    assert cli._select_driver() == 'testdriver'


def test_select_plugins(mock_pkg_resources, mock_input):
    plugs = (Mock(), Mock(), Mock())
    plugs[0].name = "test_process"
    plugs[1].name = "test_process2"
    plugs[2].name = "test_output"
    mock_pkg_resources.iter_entry_points.return_value = plugs

    mock_input.side_effect = ('a', '1', '2', '3', '2', '')
    assert cli._select_plugins() == ["test_process", "test_output"]

    mock_input.side_effect = ('1', '2', '3', '')
    assert cli._select_plugins(['test_process']) == ["test_process2",
                                                     "test_output"]


def test_setup_processing_pipeline(mock_plugin_mgr, mock_input, config):
    mock_input.return_value = "test_process2,test_process"
    cli._setup_processing_pipeline(config)
    assert config["plugins"].get() == ["test_process2", "test_process",
                                       "test_output"]

    mock_input.side_effect = ("test_process,test_process2,baz",
                              "test_process,test_process2")
    cli._setup_processing_pipeline(config)
    assert mock_input.call_count == 3
    assert config["plugins"].get() == ["test_process", "test_process2",
                                       "test_output"]


def test_set_device_target_page(config, mock_getch, mock_driver_mgr):
    mock_getch.return_value = " "

    mock_driver_mgr.return_value.driver.num_devices = 1
    cli._set_device_target_page(config, 'even')

    mock_driver_mgr.return_value.driver.num_devices = 2
    with pytest.raises(cli.DeviceException):
        cli._set_device_target_page(config, 'even')

    mock_driver_mgr.return_value.driver.num_devices = 0
    with pytest.raises(cli.DeviceException):
        cli._set_device_target_page(config, 'even')

    mock_driver_mgr.return_value.driver.num_devices = 2


def test_configure(mock_pkg_resources, mock_driver_mgr, mock_plugin_mgr,
                   config, mock_input, mock_getch):
    mockdriver = Mock()
    mockdriver.name = "testdriver"
    mockplugs = [Mock(), Mock(), Mock()]
    mockplugs[0].name = "test_process"
    mockplugs[1].name = "test_process2"
    mockplugs[2].name = "test_output"
    mock_pkg_resources.iter_entry_points.side_effect = [(mockdriver, ),
                                                        mockplugs]
    # We need to mock out all methods that touch the filesystem
    config.config_dir = Mock(return_value='/tmp/foo')
    config.dump = Mock()
    mock_getch.return_value = " "
    mock_input.side_effect = (
        "1",  # Select device driver
        "1",  # Select plugin 'test_output'
        "2",  # Select plugin 'test_process'
        "",   # Finish plugin selection
        "test_process",  # Set processing pipeline
        "y",  # Start setting target pages,
        "y",  # Confirm focus setting
    )

    mock_driver_mgr.return_value.driver.num_devices = 1

    cli.configure(config)

    mock_driver_mgr.return_value.driver.num_devices = 2

    assert config['driver'].get() == 'testdriver'
    assert config['plugins'].get() == ["test_process", "test_output"]
    assert config["device"]["focus_distance"].get() == 300
    assert config.dump.called_once_with('/tmp/foo')


@patch("select.select")
@patch('spreads.cli.sys.stdin')
@patch('spreads.cli.termios')
@patch("spreads.cli.tty")
def test_capture(tty, termios, stdin, select, config, mock_driver_mgr,
                 mock_plugin_mgr, capsys, tmpdir):
    select.return_value = ([stdin], [], [])
    stdin.read.side_effect = chain(repeat('b', 3), 'r', 'f')
    config['path'] = unicode(tmpdir)
    cli.capture(config)
    assert stdin.read.call_count == 5
    last_status = capsys.readouterr()[0].split('\r')[-1]
    assert " 6 pages " in last_status


def test_capture_nodevices(config, mock_driver_mgr, mock_plugin_mgr, tmpdir):
    config['path'] = unicode(tmpdir)
    mock_driver_mgr.return_value.driver.num_devices = 0
    with pytest.raises(DeviceException):
        cli.capture(config)
    mock_driver_mgr.return_value.driver.num_devices = 2


def test_capture_no_target_page(config, mock_driver_mgr, mock_plugin_mgr,
                                tmpdir):
    config['path'] = unicode(tmpdir)
    mock_driver_mgr.return_value.driver.target_pages = False
    with pytest.raises(DeviceException):
        cli.capture(config)
    mock_driver_mgr.return_value.driver.target_pages = True


def test_postprocess(config, mock_plugin_mgr, tmpdir):
    config['path'] = unicode(tmpdir)
    # NOTE: Nothing to assert here, we just check that it runs with our dummy
    # environment
    cli.postprocess(config)


def test_output(config, mock_plugin_mgr, tmpdir):
    config['path'] = unicode(tmpdir)
    # NOTE: Nothing to assert here, we just check that it runs with our dummy
    # environment
    cli.output(config)


@patch('spreads.cli.capture')
@patch('spreads.cli.postprocess')
@patch('spreads.cli.output')
def test_wizard(capture, postprocess, output, config):
    cli.wizard(config)
    capture.assert_called_with(config)
    postprocess.assert_called_with(config)
    output.assert_called_with(config)


def test_setup_parser(mock_plugin_mgr, config):
    parser = cli.setup_parser(config)
    subparsers = next(x._name_parser_map for x in parser._actions
                      if hasattr(x, '_name_parser_map'))
    assert len(subparsers) == 6
    assert 'test' in subparsers
    process_opts = subparsers['postprocess']._option_string_actions
    assert "--an-integer" in process_opts
    assert process_opts["--an-integer"].dest == 'test_process2.an_integer'
    assert process_opts["--an-integer"].type == int
    assert "--no-a-boolean" in process_opts
    assert process_opts["--no-a-boolean"].help == 'Disable a boolean'
    assert "--float" in process_opts
    assert process_opts["--float"].type == float
    output_opts = subparsers['output']._option_string_actions
    assert "--selectable" in output_opts
    assert output_opts["--selectable"].choices == ['a', 'b', 'c']


@patch('os.path.exists')
@patch('spreads.cli.confit.LazyConfig')
def test_main(LazyConfig, exists, config, mock_plugin_mgr,
              mock_driver_mgr, tmpdir):
    config["loglevel"] = "info"
    config["verbose"] = False
    config["logfile"] = unicode(tmpdir.join('spreads.log'))
    LazyConfig.return_value = config
    exists.return_value = False
    # NOTE: We mock out parser, since it interferes with pytest's parser
    with patch('spreads.cli.argparse.ArgumentParser'):
        cli.main()

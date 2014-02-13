from contextlib import nested

import mock
import pytest
import spreads.vendor.confit as confit

import spreads.util as util
import spreadsplug.dev.chdkcamera as chdkcamera


@pytest.fixture
def config():
    config = confit.Configuration('test_chdkcamera')
    tmpl = chdkcamera.CHDKCameraDevice.configuration_template()
    for key, option in tmpl.items():
        if option.selectable:
            config[key] = option.value[0]
        else:
            config[key] = option.value
    config['chdkptp_path'] = u'/tmp/chdkptp'
    return config


@pytest.fixture
@mock.patch('spreadsplug.dev.chdkcamera.CHDKCameraDevice._execute_lua')
@mock.patch('spreadsplug.dev.chdkcamera.CHDKCameraDevice._get_target_page')
@mock.patch('spreadsplug.dev.chdkcamera.usb')
def camera_nomock(usb, gtp, lua, config):
    gtp.return_value = 'odd'
    usbdev = mock.Mock()
    usbdev.bus, usbdev.address = 1, 2
    lua.return_value = {'build_revision': 3000}
    usb.util.get_string.return_value = b'12345678\x00\x00\x00'
    return chdkcamera.CHDKCameraDevice(config, usbdev)


@pytest.yield_fixture
def camera(camera_nomock):
    with nested(
            mock.patch.object(camera_nomock, '_run'),
            mock.patch.object(camera_nomock, '_execute_lua')):
        yield camera_nomock


@pytest.fixture
@mock.patch('spreadsplug.dev.chdkcamera.CanonA2200CameraDevice._execute_lua')
@mock.patch('spreadsplug.dev.chdkcamera.usb')
def a2200(usb, lua, config):
    usbdev = mock.Mock()
    usbdev.bus, usbdev.address = 1, 2
    lua.return_value = {'build_revision': 3000}
    usb.util.get_string.return_value = b'12345678\x00\x00\x00'
    return chdkcamera.CanonA2200CameraDevice(config, usbdev)


def test_configuration_template():
    tmpl = chdkcamera.CHDKCameraDevice.configuration_template()
    assert 'parallel_capture' in tmpl
    assert 'flip_target_pages' in tmpl


@mock.patch('spreadsplug.dev.chdkcamera.CHDKCameraDevice._execute_lua')
@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_yield_devices(usb, lua, config):
    match_cfg = mock.Mock()
    match_cfg.bInterfaceClass = 0x6
    match_cfg.bInterfaceSubClass = 0x1
    nomatch_cfg = mock.Mock()
    nomatch_cfg.bInterfaceClass = 0x3
    nomatch_cfg.bInterfaceSubClass = 0x3
    mock_devs = [mock.Mock() for x in xrange(10)]
    for dev in mock_devs:
        dev.get_active_configuration.return_value = {(0, 0): nomatch_cfg}
    mock_devs[-1].get_active_configuration.return_value = {(0, 0): match_cfg}
    mock_devs[-1].bus, mock_devs[-1].address = 1, 1
    mock_devs[-2].get_active_configuration.return_value = {(0, 0): match_cfg}
    mock_devs[-2].bus, mock_devs[-2].address = 2, 1
    usb.core.find.return_value = mock_devs
    lua.return_value = {'build_revision': 3000}
    usb.util.get_string.side_effect = (b'12345678\x00\x00\x00',
                                       b'87654321\x00\x00\x00')
    devs = list(chdkcamera.CHDKCameraDevice.yield_devices(config))
    assert len(devs) == 2
    assert devs[0]._serial_number == '12345678'
    assert devs[1]._serial_number == '87654321'


@mock.patch('spreadsplug.dev.chdkcamera.CHDKCameraDevice._execute_lua')
@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_init_noremote(usb, lua, config):
    usbdev = mock.Mock()
    usbdev.bus, usbdev.address = 1, 2
    lua.return_value = {'build_revision': 2500}
    usb.util.get_string.return_value = b'12345678\x00\x00\x00'
    dev = chdkcamera.CHDKCameraDevice(config, usbdev)
    assert dev._can_remote is False


@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_connected(usb, camera):
    usb.core.find.return_value = True
    assert camera.connected()


@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_reconnected(usb, camera):
    newdev = mock.Mock(bus=3, address=1)
    usb.core.find.side_effect = [None, newdev]
    assert camera.connected()
    assert camera._usbport == (3, 1)


@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_not_connected(usb, camera):
    usb.core.find.return_value = None
    assert not camera.connected()


@mock.patch('spreadsplug.dev.chdkcamera.os.write')
def test_set_target_page(write, camera):
    camera.set_target_page('odd')
    assert write.call_args_list[0][0][1] == "ODD\n"
    assert camera.target_page == 'odd'


def test_prepare_capture(camera):
    camera.prepare_capture('/tmp/foo')
    camera._execute_lua.assert_any_call('enter_alt()')
    camera._run.assert_any_call('rec')


def test_prepare_capture_withrec(camera):
    camera._run.side_effect = chdkcamera.CHDKPTPException()
    camera.prepare_capture('/tmp/foo')
    camera._execute_lua.assert_any_call('enter_alt()')
    camera._run.assert_any_call('rec')


def test_finish_capture(camera):
    camera.finish_capture()
    camera._run.assert_called_once_with('play')


@mock.patch('__builtin__.open')
def test_get_preview_image(mock_open, camera):
    fhandle = mock_open.return_value.__enter__.return_value
    fhandle.read.return_value = 'foobar'
    assert camera.get_preview_image() == 'foobar'


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera.capture('/tmp/000')
    assert camera._run.call_count == 1
    assert camera._run.call_args_list[0][0][0].startswith('remoteshoot')
    assert jpeg.called_once_with('/tmp/000.jpg')
    assert jpeg.return_value.orientation == 8
    assert jpeg.return_value.save.called_once_with('/tmp/000.jpg')


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_raw(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera._shoot_raw = True
    camera.capture('/tmp/000')
    assert camera._run.call_count == 1
    assert "-dng " in camera._run.call_args_list[0][0][0]
    assert jpeg.called_once_with('/tmp/000.dng')


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_noprepare(jpeg, camera):
    camera._run.side_effect = (
        chdkcamera.CHDKPTPException('dev not in rec mode'), None)
    with mock.patch.object(camera, 'prepare_capture') as prepare:
        camera.capture('/tmp/000')
        assert prepare.call_count == 1
        assert camera._run.call_count == 2


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_noremote(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera._can_remote = False
    camera.capture('/tmp/000')
    assert camera._run.call_count == 1
    assert camera._run.call_args_list[0][0][0].startswith('shoot')


def test_capture_error(camera):
    camera._run.side_effect = chdkcamera.CHDKPTPException('foobar')
    with pytest.raises(chdkcamera.CHDKPTPException) as exc:
        camera.capture('/tmp/000')
        assert exc is camera._run.side_effect


@mock.patch('spreadsplug.dev.chdkcamera.subprocess')
def test_run(sp, camera_nomock):
    sp.check_output.return_value = (
        "connected: foo bar \n"
        "asdf")
    output = camera_nomock._run('foobar')
    assert output == ["asdf"]
    sp.check_output.assert_called_with(
        [u'/tmp/chdkptp/chdkptp', '-c-d=002 -b=001', '-eset cli_verbose=2',
            '-efoobar'], env={'LUA_PATH': u'/tmp/chdkptp/lua/?.lua'},
        stderr=sp.STDOUT)


@mock.patch('spreadsplug.dev.chdkcamera.subprocess')
def test_run_with_error(sp, camera_nomock):
    sp.check_output.return_value = (
        "connected: foo bar \n"
        "ERROR: foobar")
    with pytest.raises(chdkcamera.CHDKPTPException) as exc:
        camera_nomock._run('foobar')
        assert 'ERROR: foobar' in exc.message


def test_execute_lua(camera_nomock):
    camera = camera_nomock
    with mock.patch.object(camera, '_run') as run:
        camera._execute_lua("foobar")
        run.assert_called_with("luar foobar")


def test_execute_lua_nowait(camera_nomock):
    camera = camera_nomock
    with mock.patch.object(camera, '_run') as run:
        camera._execute_lua("foobar", wait=False)
        run.assert_called_with("lua foobar")


def test_execute_lua_with_get_result(camera_nomock):
    camera = camera_nomock
    with mock.patch.object(camera, '_run') as run:
        run.return_value = ["10:return:'bar'"]
        assert camera._execute_lua("foo", get_result=True) == "bar"


def test_execute_lua_with_get_result_hasreturn(camera_nomock):
    camera = camera_nomock
    with mock.patch.object(camera, '_run') as run:
        camera._run.return_value = ["10:return:5"]
        out = camera._execute_lua("return moo", get_result=True)
        run.assert_called_with("luar return moo")
        assert out == 5


def test_parse_luatable(camera):
    data = "table:foo=\"bar\",bar=123"
    parsed = camera._parse_table(data)
    assert parsed == {'foo': 'bar', 'bar': 123}


@mock.patch('__builtin__.open')
def test_get_target_page(mock_open, camera):
    fhandle = mock_open.return_value.__enter__.return_value
    fhandle.readline.return_value = 'ODD'
    target_page = camera._get_target_page()
    assert target_page == 'odd'


def test_get_target_page_error(camera):
    camera._run.side_effect = [util.DeviceException]
    with pytest.raises(ValueError):
        camera._get_target_page()


def test_set_zoom(camera):
    camera._zoom_steps = 8
    with pytest.raises(ValueError):
        camera._set_zoom(10)
    camera._set_zoom(7)
    camera._execute_lua.assert_called_once_with("set_zoom(7)", wait=True)


@mock.patch('spreadsplug.dev.chdkcamera.time.sleep')
def test_acquire_focus(sleep, camera):
    camera._run.side_effect = chdkcamera.CHDKPTPException()
    camera._execute_lua.side_effect = (None, None, None, None, None, 300)
    assert camera._acquire_focus() == 300
    assert camera._run.call_count == 1


@mock.patch('spreadsplug.dev.chdkcamera.time.sleep')
def test_set_focus(sleep, camera):
    camera._focus_distance = 'auto'
    camera._set_focus()
    assert camera._execute_lua.call_count == 1
    camera._focus_distance = 300
    camera._set_focus()
    assert camera._execute_lua.call_count > 1


@mock.patch('spreadsplug.dev.chdkcamera.CanonA2200CameraDevice._execute_lua')
@mock.patch('spreadsplug.dev.chdkcamera.usb')
def test_a2200_yield_devices(usb, lua, config):
    mock_devs = [mock.Mock(idProduct=0xff, idVendor=0xff) for x in xrange(10)]
    mock_devs[-1].idProduct, mock_devs[-1].idVendor = 0x322a, 0x4a9
    mock_devs[-1].bus, mock_devs[-1].address = 1, 1
    mock_devs[-2].idProduct, mock_devs[-2].idVendor = 0x322a, 0x4a9
    mock_devs[-2].bus, mock_devs[-2].address = 2, 1
    usb.core.find.return_value = mock_devs
    lua.return_value = {'build_revision': 3000}
    usb.util.get_string.side_effect = (b'12345678\x00\x00\x00',
                                       b'87654321\x00\x00\x00')
    devs = list(chdkcamera.CanonA2200CameraDevice.yield_devices(config))
    assert len(devs) == 2
    assert devs[0]._serial_number == '12345678'
    assert devs[1]._serial_number == '87654321'


def test_a2200_finish_capture(a2200):
    with mock.patch.object(a2200, '_run') as run:
        a2200.finish_capture()
        assert run.call_count == 0


def test_a2200_set_zoom(a2200):
    a2200._zoom_steps = 8
    with pytest.raises(ValueError):
        a2200._set_zoom(10)
    with mock.patch.object(a2200, '_execute_lua') as lua:
        lua.return_value = 1
        a2200._set_zoom(7)
        lua.return_value = 8
        a2200._set_zoom(7)
        assert lua.call_count == 4

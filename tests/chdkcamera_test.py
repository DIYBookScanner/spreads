# FIXME: Adapt to new chdkptp.py backenD
#   The testing-boundary are the calls into chdkptp.py, so we just have
#   to mock chdkptp.ChdkDevice and chdkptp.list_devices

import itertools

import chdkptp
import mock
import pytest
import spreads.vendor.confit as confit

import spreadsplug.dev.chdkcamera as chdkcamera


@pytest.fixture
def config(tmpdir):
    config = confit.Configuration('test_chdkcamera')
    tmpl = chdkcamera.CHDKCameraDevice.configuration_template()
    for key, option in tmpl.items():
        if option.selectable:
            config[key] = option.value[0]
        else:
            config[key] = option.value
    return config


@pytest.yield_fixture
def chdkdev():
    with mock.patch(
            'spreadsplug.dev.chdkcamera.chdkptp.ChdkDevice') as mockdev:
        rv = mockdev.return_value
        # Mock values needed for initialization
        rv.lua_execute.side_effect = itertools.cycle(
            [{'build_revision': 3000}, 8, None])
        rv.info = chdkptp.DeviceInfo(
            'foo', 0, 0, 0x1337, 0x1337, 'deadbeef', '1337')
        yield rv


@pytest.fixture
def camera(chdkdev, config):
    return chdkcamera.CHDKCameraDevice(config, chdkdev)


def test_configuration_template():
    tmpl = chdkcamera.CHDKCameraDevice.configuration_template()
    assert 'parallel_capture' in tmpl
    assert 'flip_target_pages' in tmpl


@mock.patch('spreadsplug.dev.chdkcamera.chdkptp.list_devices')
def test_yield_devices(list_dev, chdkdev, config):
    # TODO: Create two DeviceInfo objects, one with an id matching
    # the QualityFix special case
    infos = [
        chdkptp.DeviceInfo('qualfix', 0, 0, 0x4a9, 0x31ef, 'deadbeef', '1337'),
        chdkptp.DeviceInfo('other', 0, 1, 0x1337, 0x1337, 'beefdead', '31337')
    ]
    list_dev.return_value = infos
    devs = list(chdkcamera.CHDKCameraDevice.yield_devices(config))
    assert devs[0]._zoom_steps == 8
    assert devs[1]._chdk_buildnum == 3000
    assert isinstance(devs[0], chdkcamera.QualityFix)
    assert isinstance(devs[1], chdkcamera.CHDKCameraDevice)


def test_init_noremote(chdkdev):
    chdkdev.lua_execute.side_effect = [{'build_revision': 2926}, 8, None]
    dev = chdkcamera.CHDKCameraDevice(config, chdkdev)
    assert dev._can_remote is False


def test_connected(camera):
    camera._device.is_connected = True
    assert camera.connected()


def test_reconnected(camera):
    camera._device.is_connected = False
    assert camera.connected()
    assert camera._device.reconnect.call_count == 1
    camera._device.reconnect.side_effect = chdkptp.lua.PTPError(mock.Mock())
    assert not camera.connected()


def test_not_connected(camera):
    camera._device.is_connected = False
    camera._device.reconnect.side_effect = chdkptp.lua.PTPError(mock.Mock())
    assert not camera.connected()


@mock.patch('spreadsplug.dev.chdkcamera.os.write')
def test_set_target_page(write, camera):
    camera.set_target_page('odd')
    assert write.call_args_list[0][0][1] == "ODD\n"
    assert camera.target_page == 'odd'
    assert camera._device.upload_file.call_count == 1


def test_prepare_capture(camera):
    camera.prepare_capture()
    camera._device.lua_execute.assert_any_call('enter_alt()')
    camera._device.switch_mode.assert_any_call('rec')


@pytest.mark.xfail  # See docstring for `finish_capture` for details
def test_finish_capture(camera):
    camera.finish_capture()
    camera._run.assert_called_once_with('play')


def test_get_preview_image(camera):
    camera._device.get_frames.return_value = itertools.repeat("foo")
    assert camera.get_preview_image() == "foo"


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera._device.mode = 'rec'
    fpath = mock.MagicMock()
    fpath.__unicode__.return_value = '/tmp/000.jpg'
    fpath.__str__.return_value = '/tmp/000.jpg'
    camera.target_page = 'odd'
    camera.capture(fpath)
    assert camera._device.capture.call_count == 1
    cap_args = tuple(camera._device.capture.mock_calls[0])[-1]
    assert not cap_args['dng']
    assert cap_args['stream']
    assert jpeg.called_once_with('/tmp/000.jpg')
    assert jpeg.return_value.exif_orientation == 6
    assert jpeg.return_value.save.called_once_with('/tmp/000.jpg')


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_raw(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera.config['shoot_raw'] = True
    camera._device.mode = 'rec'
    fpath = mock.MagicMock()
    fpath.__unicode__.return_value = '/tmp/000.jpg'
    fpath.__str__.return_value = '/tmp/000.jpg'
    camera.target_page = 'odd'
    camera.capture(fpath)
    cap_args = tuple(camera._device.capture.mock_calls[0])[-1]
    assert cap_args['dng']


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_noprepare(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera._device.mode = 'play'
    camera.target_page = 'odd'
    camera.capture(mock.MagicMock())
    camera._device.switch_mode.assert_called_once_with("rec")


@mock.patch('spreadsplug.dev.chdkcamera.JPEGImage')
def test_capture_noremote(jpeg, camera):
    jpeg.return_value = mock.Mock()
    camera._device.mode = 'rec'
    camera._can_remote = False
    camera.target_page = 'odd'
    camera.capture(mock.MagicMock())
    cap_args = tuple(camera._device.capture.mock_calls[0])[-1]
    assert not cap_args['stream']
    assert cap_args['download_after']
    assert cap_args['remove_after']


def test_capture_error(camera):
    camera._device.capture.side_effect = chdkcamera.CHDKPTPException('foobar')
    camera._device.mode = 'rec'
    with pytest.raises(chdkcamera.CHDKPTPException) as exc:
        camera.capture(mock.MagicMock())
        assert exc is camera._device.capture.side_effect


def test_get_target_page(camera):
    camera._device.download_file.return_value = "ODD\n\n"
    target_page = camera._get_target_page()
    assert target_page == 'odd'


def test_get_target_page_error(camera):
    camera._device.download_file.side_effect = chdkptp.lua.PTPError(
        mock.Mock())
    with pytest.raises(ValueError):
        camera._get_target_page()


def test_set_zoom(camera):
    camera._zoom_steps = 8
    camera.config['zoom_level'] = 10
    with pytest.raises(ValueError):
        camera._set_zoom()
    camera.config['zoom_level'] = 7
    camera._set_zoom()
    camera._device.lua_execute.assert_called_with("set_zoom(7)")


@mock.patch('spreadsplug.dev.chdkcamera.time.sleep')
def test_acquire_focus(sleep, camera):
    camera._device.lua_execute.side_effect = (
        None, None, None, None, None, 300)
    assert camera._acquire_focus() == 300


@mock.patch('spreadsplug.dev.chdkcamera.time.sleep')
def test_set_focus(sleep, camera):
    camera.config['focus_mode'] = 'autofocus_all'
    camera._set_focus()
    camera._device.lua_execute.assert_called_with("set_aflock(0)")
    camera._device.lua_execute.reset_mock()
    camera.config['focus_mode'] = 'manual'
    camera.config['focus_distance'] = 300
    camera._set_focus()
    assert camera._device.lua_execute.call_count == 2

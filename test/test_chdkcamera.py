from itertools import chain, repeat

from mock import MagicMock as Mock
from nose.tools import assert_raises
from pyptpchdk import PTPError

import spreads
import spreadsplug.dev.chdkcamera as chdkcamera

spreads.util.find_in_path = Mock(return_value=True)


class TestPTPDevice(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        chdkcamera.pyptpchdk = Mock()
        chdkcamera.time = Mock()
        usbmock = Mock()
        usbmock.bus, usbmock.address = 1, 2
        self.dev = chdkcamera.PTPDevice(usbmock)

    def test_execute_lua(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkScriptStatus.side_effect = [1]
        self.dev.execute_lua("foobar")
        chdkcamera.pyptpchdk.PTPDevice.assert_called_with(1, 2)
        self.dev._device.chdkExecLua.assert_called_with("foobar")

    def test_execute_lua_nowait(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkScriptStatus.side_effect = [1]
        self.dev.execute_lua("foobar", wait=False)
        chdkcamera.pyptpchdk.PTPDevice.assert_called_with(1, 2)
        self.dev._device.chdkExecLua.assert_called_with("foobar")

    def test_execute_lua_with_intermittent_error(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkExecLua.side_effect = [Exception, Exception, 1]
        self.dev._device.chdkScriptStatus.side_effect = [1]
        self.dev.execute_lua("foobar")
        self.dev._device.chdkExecLua.assert_called_with("foobar")

    def test_execute_lua_with_persistent_error(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkExecLua.side_effect = Exception
        self.dev._device.chdkScriptStatus.side_effect = [1]
        assert_raises(spreads.util.DeviceException, self.dev.execute_lua,
                      "foobar")

    def test_execute_lua_with_intermittent_timeout(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkExecLua.return_value = 1
        self.dev._device.chdkScriptStatus.side_effect = (
            chain((PTPError,), repeat(0, 255), (1, )))
        self.dev.execute_lua("foobar")
        self.dev._device.chdkExecLua.assert_called_with("foobar")

    def test_execute_lua_with_persistent_timeout(self):
        self.dev._flush_messages = Mock()
        self.dev._device.chdkExecLua.return_value = 1
        self.dev._device.chdkScriptStatus.return_value = 0
        assert_raises(spreads.util.DeviceException, self.dev.execute_lua,
                      "foobar")

    def test_execute_lua_with_get_result(self):
        self.dev._get_messages = Mock(side_effect=["bar"])
        self.dev._device.chdkScriptStatus.side_effect = [1]
        assert self.dev.execute_lua("foo", get_result=True) == "bar"
        chdkcamera.pyptpchdk.PTPDevice.assert_called_with(1, 2)
        self.dev._device.chdkExecLua.assert_called_with("return(foo)")

    def test_execute_lua_with_get_result_hasreturn(self):
        self.dev._get_messages = Mock()
        self.dev._device.chdkScriptStatus.side_effect = [1]
        self.dev.execute_lua("return(moo)", get_result=True)
        self.dev._device.chdkExecLua.assert_called_with("return(moo)")

    def test_get_messages(self):
        self.dev._device.chdkReadScriptMessage.side_effect = (
            [("foobar", 0, 1234), (0, 0, 0)])
        msg = self.dev._get_messages(1234)
        assert msg == ("foobar", )

    def test_get_messages_readerror(self):
        self.dev._device.chdkReadScriptMessage.side_effect = (
            [PTPError, ("foobar", 0, 1234), (0, 0, 0)])
        assert self.dev._get_messages(1234) == ("foobar", )

    def test_get_messages_luaerror(self):
        self.dev._device.chdkReadScriptMessage.side_effect = (
            [("foobar", 1, 1234), (0, 0, 0)])
        assert_raises(spreads.util.DeviceException, self.dev._get_messages, 1234)

    def test_get_messages_idmismatch(self):
        self.dev._device.chdkReadScriptMessage.side_effect = (
            [("foobar", 2, 4321), ("foobar", 2, 1234), (0, 0, 0)])
        msg = self.dev._get_messages(1234)
        assert msg == ("foobar", )

    def test_flush_messages(self):
        self.dev._device.chdkReadScriptMessage.side_effect = [
            (0, 0, x) for x in reversed(xrange(10))]
        self.dev._flush_messages()
        assert self.dev._device.chdkReadScriptMessage.call_count == 10

    def test_flush_messages_error(self):
        self.dev._device.chdkReadScriptMessage.side_effect = repeat(PTPError)
        assert self.dev._flush_messages() is None
        assert self.dev._device.chdkReadScriptMessage.call_count == 11

    def test_get_orientation(self):
        self.dev._get_messages = Mock(return_value=['LEFT'])
        assert self.dev.get_orientation() == 'left'
        # Test caching
        assert self.dev.get_orientation() == 'left'
        assert self.dev._get_messages.call_count == 1

    def test_get_orientation_error(self):
        self.dev._get_messages = Mock(
            side_effect=[spreads.util.DeviceException])
        assert self.dev.get_orientation() == None

    def test_set_orientation(self):
        self.dev._flush_messages = Mock()
        self.dev.set_orientation('left')
        assert self.dev._orientation == 'left'

    def test_get_image_list(self):
        # TODO: Get camera output to mock the execute_lua call
        pass

    def test_download_image(self):
        self.dev._device.chdkDownload = Mock()
        mock_img = Mock()
        chdkcamera.pexif.JpegFile.fromFile = Mock(return_value=mock_img)
        self.dev._orientation = 'right';
        self.dev.download_image('/foo/bar.JPG', '/tmp/moo.JPG')
        assert mock_img.exif.primary.Orientation == [6]
        self.dev._orientation = 'left';
        self.dev.download_image('/foo/bar.JPG', '/tmp/moo.JPG')
        assert mock_img.exif.primary.Orientation == [8]

    def test_download_all_images(self):
        self.dev.get_image_list = Mock(return_value=repeat('foo.jpg', 10))
        self.dev.download_image = Mock()
        self.dev.download_all_images('/tmp')
        assert self.dev.download_image.call_count == 10

    def test_delete_image(self):
        # Not much to test here, but let's do it for our coverage vanity...
        self.dev.execute_lua = Mock()
        self.dev.delete_image('/a/b.jpg')

    def test_delete_all_images(self):
        self.dev.get_image_list = Mock(return_value=repeat('foo.jpg', 10))
        self.dev.delete_image = Mock()
        self.dev.delete_all_images()
        assert self.dev.delete_image.call_count == 10

    def test_get_preview_image(self):
        # Pure vanity....
        chdkcamera.Image = Mock()
        chdkcamera.pyptpchdk.LiveViewFlags.VIEWPORT = 1
        chdkcamera.pyptpchdk.LiveViewFlags.BITMAP = 2
        self.dev.get_preview_image(viewport=True, ui_overlay=True)
        self.dev._device.chdkGetLiveData.assert_called_with(3)

from itertools import chain, repeat

from mock import MagicMock as Mock, patch, call
from nose.tools import assert_raises, raises
from pyptpchdk import PTPError

import spreads.confit as confit
import spreads.util as util
import spreadsplug.dev.chdkcamera as chdkcamera

util.find_in_path = Mock(return_value=True)


class TestChdkCameraDevice(object):
    def setUp(self):
        chdkcamera.subprocess.check_output = Mock()
        usbmock = Mock()
        usbmock.bus, usbmock.address = 1, 2
        self.config = confit.Configuration('test_chdkcamera')
        tmpl = chdkcamera.CHDKCameraDevice.configuration_template()
        for key, option in tmpl.items():
            if option.selectable:
                self.config[key] = option.value[0]
            else:
                self.config[key] = option.value
        self.config['chdkptp_path'] = u'/tmp/chdkptp'
        with patch('spreadsplug.dev.chdkcamera.'
                   'CHDKCameraDevice._execute_lua') as lua:
            lua.return_value = {'build_revision': 3000}
            self.dev = chdkcamera.CHDKCameraDevice(self.config, usbmock)

    def test_init_noremote(self):
        usbmock = Mock()
        usbmock.bus, usbmock.address = 1, 2
        with patch('spreadsplug.dev.chdkcamera.'
                   'CHDKCameraDevice._execute_lua') as lua:
            lua.return_value = {'build_revision': 2500}
            dev = chdkcamera.CHDKCameraDevice(self.config, usbmock)
            assert dev._can_remote is False

    def test_run(self):
        chdkcamera.subprocess.check_output.return_value = (
            "connected: foo bar \n"
            "asdf")
        output = self.dev._run('foobar')
        assert output == ["asdf"]
        assert (call([u'/tmp/chdkptp/chdkptp', '-c-d=002 -b=001', '-efoobar'],
                     env={'LUA_PATH': u'/tmp/chdkptp/lua/?.lua'}, stderr=-2)
                in chdkcamera.subprocess.check_output.call_args_list)

    def test_execute_lua(self):
        self.dev._run = Mock()
        self.dev._execute_lua("foobar")
        self.dev._run.assert_called_with("luar foobar")

    def test_execute_lua_nowait(self):
        self.dev._run = Mock()
        self.dev._execute_lua("foobar", wait=False)
        self.dev._run.assert_called_with("lua foobar")

    def test_execute_lua_with_get_result(self):
        self.dev._run = Mock()
        self.dev._run.return_value = ["10:return:'bar'"]
        assert self.dev._execute_lua("foo", get_result=True) == "bar"

    def test_execute_lua_with_get_result_hasreturn(self):
        self.dev._run = Mock()
        self.dev._run.return_value = ["10:return:5"]
        out = self.dev._execute_lua("return moo", get_result=True)
        assert out == 5
        self.dev._run.assert_called_with("luar return moo")

    def test_get_orientation(self):
        self.dev._run = Mock()
        with patch('spreadsplug.dev.chdkcamera.open',
                   create=True) as mock_open:
            mock_open.return_value = Mock(spec=file)
            fhandle = mock_open.return_value.__enter__.return_value
            fhandle.readline.return_value = 'LEFT'
            orientation = self.dev._get_orientation()
        assert orientation == 'left'

    @raises(ValueError)
    def test_get_orientation_error(self):
        self.dev._run = Mock()
        self.dev._run.side_effect = [util.DeviceException]
        self.dev._get_orientation()

    @patch('spreadsplug.dev.chdkcamera.os.write')
    def test_set_orientation(self, write):
        self.dev._run = Mock()
        self.dev.set_orientation('left')
        assert self.dev.orientation == 'left'

    def test_get_preview_image(self):
        self.dev._run = Mock()
        with patch('spreadsplug.dev.chdkcamera.open',
                   create=True) as mock_open:
            fhandle = mock_open.return_value.__enter__.return_value
            fhandle.read.return_value = 'foobar'
            data = self.dev.get_preview_image()
        assert data == 'foobar'

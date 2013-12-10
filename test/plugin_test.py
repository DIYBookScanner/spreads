from mock import call, MagicMock as Mock, patch
from nose.tools import raises

import spreads
import spreads.plugin as plugin
from spreads.util import DeviceException


class TestPlugin(object):
    def setUp(self):
        reload(plugin)
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = []

    def test_pluginmanager(self):
        plugin.SpreadsNamedExtensionManager = Mock()
        pm = plugin.get_pluginmanager()
        pm_new = plugin.get_pluginmanager()
        assert pm is pm_new

    def test_get_devices(self):
        device = Mock()
        device.match = Mock(return_value=True)
        device.__name__ = "Mock"
        usb_mock = Mock()
        extension_mock = Mock()
        plugin.usb.core.find = Mock(return_value=[usb_mock])
        plugin.DriverManager = Mock(return_value=extension_mock)
        extension_mock.driver = device
        plugin.get_devices()
        assert call(spreads.config, usb_mock) in device.call_args_list
        assert device.match.call_args_list == [call(usb_mock)]

    @raises(DeviceException)
    def test_no_devices(self):
        device_a = Mock()
        device_a.plugin.match = Mock(return_value=True)
        device_b = Mock()
        device_b.plugin.match = Mock(return_value=False)
        plugin.usb.core.find = Mock(return_value=[])
        dm = Mock()
        dm.map = lambda x, y: [x(z, y) for z in [device_a, device_b]]
        plugin.get_devicemanager = Mock(return_value=dm)
        plugin.get_devices()

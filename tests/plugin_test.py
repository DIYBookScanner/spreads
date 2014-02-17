import pytest

import spreads.plugin as plugin


def test_get_devices(config, mock_driver_mgr):
    devices = plugin.get_devices(config)
    assert len(devices) == 2
    assert devices[0].__name__ == 'testdriver'
    assert devices[0]._id != devices[1]._id


def test_set_default_config(config, mock_driver_mgr, mock_plugin_mgr):
    # TODO: This should be moved to the config-tests
    config.load_defaults()
    assert config["test_process"]["a_boolean"].get()
    assert config["test_process"]["float"].get() == 3.14
    assert config["test_process2"]["an_integer"].get() == 10
    assert config["test_process2"]["list"].get() == [1, 2, 3]
    assert config["test_output"]["string"].get() == "moo"
    assert config["test_output"]["selectable"].get() == "a"


def test_get_relevant_extensions(mock_plugin_mgr):
    plugin_manager = plugin.get_pluginmanager()
    exts = list(plugin.get_relevant_extensions(
        plugin_manager, [plugin.ProcessHookMixin]))
    assert len(exts) == 2
    assert exts[0].name == "test_process"
    assert exts[1].name == "test_process2"


def test_bad_driver():
    class BadDriver(plugin.DevicePlugin):
        pass

    with pytest.raises(TypeError):
        BadDriver(None, None)

import pytest

import spreads.plugin as plugin


def test_get_devices(config):
    devices = plugin.get_devices(config)
    assert len(devices) == 2
    assert devices[0].__name__ == 'testdriver'
    assert devices[0]._id != devices[1]._id


def test_set_default_config(config):
    # TODO: This should be moved to the config-tests
    config.load_defaults()
    assert config["test_process"]["a_boolean"].get()
    assert config["test_process"]["float"].get() == 3.14
    assert config["test_process2"]["an_integer"].get() == 10
    assert config["test_process2"]["list"].get() == [1, 2, 3]
    assert config["test_output"]["string"].get() == "moo"
    assert config["test_output"]["selectable"].get() == "a"


def test_bad_driver():
    class BadDriver(plugin.DevicePlugin):
        pass

    with pytest.raises(TypeError):
        BadDriver(None, None)

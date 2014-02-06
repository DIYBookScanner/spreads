import time

import mock
import pytest

import spreadsplug.intervaltrigger as intervaltrigger


@pytest.fixture
def plugin(config):
    config['intervaltrigger']['interval'] = 0.1
    return intervaltrigger.IntervalTrigger(config)


def test_trigger_loop(plugin):
    cbmock = mock.Mock()
    plugin.start_trigger_loop(cbmock)
    time.sleep(0.55)
    plugin.stop_trigger_loop()
    assert cbmock.call_count == 5

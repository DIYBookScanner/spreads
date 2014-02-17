import os.path
import shutil
import time
from random import randint

import mock
import pytest
from spreads.workflow import Workflow
from spreads.plugin import SpreadsPlugin
from spreads.util import EventHandler

import spreads.plugin as plugin
from spreads.config import Configuration, OptionTemplate


class TestPluginProcess(plugin.HookPlugin,
                        plugin.ProcessHookMixin):
    __name__ = 'test_process'

    @classmethod
    def configuration_template(cls):
        return {'a_boolean': OptionTemplate(
                    value=True, docstring="A boolean",
                    selectable=False),
                'float': OptionTemplate(
                    value=3.14, docstring="A float",
                    selectable=False)}

    def process(self, path):
        (path/'processed_a.txt').touch()


class TestPluginProcessB(TestPluginProcess):
    __name__ = 'test_process2'

    @classmethod
    def configuration_template(cls):
        return {'an_integer': OptionTemplate(
                    value=10, docstring="An integer",
                    selectable=False),
                'list': OptionTemplate(
                    value=[1, 2, 3], docstring="A list",
                    selectable=False)}

    def process(self, path):
        (path/'processed_b.txt').touch()


class TestPluginOutput(plugin.HookPlugin,
                       plugin.OutputHookMixin,
                       plugin.SubcommandHookMixin):
    __name__ = 'test_output'

    @classmethod
    def configuration_template(cls):
        return {'string': OptionTemplate(
                    value="moo", docstring="A string",
                    selectable=False),
                'selectable': OptionTemplate(
                    value=["a", "b", "c"], docstring="A selectable",
                    selectable=True)}

    @classmethod
    def add_command_parser(cls, rootparser):
        testparser = rootparser.add_parser('test', help="test subcommand")
        testparser.set_defaults(subcommand=cls.test_command)

    @staticmethod
    def test_command(config):
        pass

    def output(self, path):
        (path/'output.txt').touch()


class TestDriver(plugin.DevicePlugin):
    __name__ = 'testdriver'

    features = (plugin.DeviceFeatures.IS_CAMERA, )
    num_devices = 2
    target_pages = True
    delay = 0

    @classmethod
    def yield_devices(cls, config):
        for idx in xrange(cls.num_devices):
            instance = cls(config, None)
            if cls.target_pages:
                instance.set_target_page('odd' if idx % 2 else 'even')
            yield instance

    def __init__(self, config, device):
        self.target_page = None
        self._id = hex(randint(0, 2**32))[2:]

    def connected(self):
        return True

    def set_target_page(self, target):
        self.target_page = target

    def prepare_capture(self, path):
        pass

    def capture(self, path):
        if self.delay:
            time.sleep(self.delay)
        srcpath = os.path.abspath(
            './tests/data/{0}.jpg'.format(self.target_page or 'even')
        )
        shutil.copyfile(srcpath, unicode(path)+'.jpg')

    def finish_capture(self):
        pass

    def _acquire_focus(self):
        return 300


@pytest.fixture
def config():
    cfg = Configuration(appname='spreads_test')
    cfg["driver"] = u"testdriver"
    cfg["plugins"] = [u"test_output", u"test_process", u"test_process2"]
    cfg["capture"]["capture_keys"] = ["b", " "]
    return cfg


@pytest.yield_fixture
def mock_plugin_mgr(config):
    with mock.patch('spreads.plugin.get_pluginmanager') as get_pm:
        # TODO: Use stevedore.TestExtensionManager and real Extension instances
        #       for this
        exts = [mock.Mock(plugin=TestPluginOutput,
                          obj=TestPluginOutput(config)),
                mock.Mock(plugin=TestPluginProcess,
                          obj=TestPluginProcess(config)),
                mock.Mock(plugin=TestPluginProcessB,
                          obj=TestPluginProcessB(config))]
        exts[0].name = "test_output"
        exts[1].name = "test_process"
        exts[2].name = "test_process2"

        pm = mock.MagicMock(spec=plugin.SpreadsNamedExtensionManager)
        pm.__iter__.return_value = exts
        pm.map = lambda func, *args, **kwargs: [func(ext, *args, **kwargs)
                                                for ext in exts]
        get_pm.return_value = pm
        yield get_pm


@pytest.yield_fixture
def mock_driver_mgr():
    with mock.patch('spreads.plugin.get_driver') as get_driver:
        ext = mock.Mock(plugin=TestDriver)
        ext.name = "testdriver"
        dm = mock.MagicMock(spec=plugin.DriverManager)
        dm.driver = TestDriver
        dm.extensions = [ext]
        dm.__iter__.return_value = [ext]
        get_driver.return_value = dm
        yield get_driver


@pytest.yield_fixture(scope='module')
def mock_path():
    with mock.patch('spreads.vendor.pathlib.Path') as path:
        mockpath = mock.MagicMock(wraps='spreas.vendor.pathlib.PosixPath')
        mockpath.parent.return_value = mockpath
        mockpath.mkdir = mock.Mock()
        path.return_value = mockpath
        yield path


@pytest.yield_fixture(scope='module')
def mock_findinpath():
    with mock.patch('spreads.util.find_in_path') as find:
        find.return_value = True
        yield find


@pytest.yield_fixture(autouse=True)
def fix_blinker():
    yield
    for signal in (Workflow.on_created, Workflow.on_removed,
                   Workflow.on_modified, Workflow.on_step_progressed,
                   Workflow.on_capture_executed, SpreadsPlugin.on_progressed,
                   EventHandler.on_log_emit):
        signal._clear_state()

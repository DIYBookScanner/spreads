import logging
import os.path
import shutil
import time
from itertools import chain
from random import randint

import mock
import pytest
import spreads.workflow as workflow

import spreads.plugin as plugin
import spreads.util as util
import spreadsplug.web.handlers as handlers
from spreads.config import Configuration, OptionTemplate

logging.getLogger().level = logging.DEBUG


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

    def process(self, pages, target_path):
        for page in pages:
            proc_path = target_path/(page.raw_image.name + "_a.txt")
            proc_path.touch()
            page.processed_images[self.__name__] = proc_path


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

    def process(self, pages, target_path):
        for page in pages:
            proc_path = target_path/(page.raw_image.name + "_a.txt")
            proc_path.touch()
            page.processed_images[self.__name__] = proc_path


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
    def add_command_parser(cls, rootparser, config):
        testparser = rootparser.add_parser('test', help="test subcommand")
        testparser.set_defaults(subcommand=cls.test_command)

    @staticmethod
    def test_command(config):
        pass

    def output(self, pages, target_path, metadata, table_of_contents):
        (target_path/'output.txt').touch()


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
        shutil.copyfile(srcpath, unicode(path))

    def finish_capture(self):
        pass

    def update_configuration(self, updated):
        pass

    def _acquire_focus(self):
        return 300


@pytest.yield_fixture(autouse=True)
def mock_iter_entry_points():
    def iter_entry_points(namespace, name=None):
        if namespace == 'spreadsplug.hooks':
            exts = [mock.Mock(), mock.Mock(), mock.Mock()]
            exts[0].name = "test_output"
            exts[0].load.return_value = TestPluginOutput
            exts[1].name = "test_process"
            exts[1].load.return_value = TestPluginProcess
            exts[2].name = "test_process2"
            exts[2].load.return_value = TestPluginProcessB
            if name is None:
                return iter(exts)
            elif name == 'test_output':
                return iter((exts[0],))
            elif name == 'test_process':
                return iter((exts[1],))
            elif name == 'test_process2':
                return iter((exts[2],))
        elif namespace == 'spreadsplug.devices':
            mock_ext = mock.Mock()
            mock_ext.name = 'testdriver'
            mock_ext.load.return_value = TestDriver
            return iter((mock_ext,))
    with mock.patch('spreads.plugin.pkg_resources') as pkg_resources:
        pkg_resources.iter_entry_points = iter_entry_points
        yield


@pytest.fixture(autouse=True)
def empty_device_cache():
    import spreads.plugin
    spreads.plugin.devices = None


@pytest.yield_fixture
def config():
    with mock.patch('spreads.config.confit.Configuration.read'):
        cfg = Configuration(appname='spreads_test')
        cfg["driver"] = u"testdriver"
        cfg["plugins"] = [u"test_output", u"test_process", u"test_process2"]
        cfg["capture"]["capture_keys"] = ["b", " "]
        cfg.load_defaults()
        yield cfg


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
        find.side_effect = lambda x: '/usr/bin/{0}'.format(x)
        yield find


@pytest.yield_fixture(autouse=True)
def fix_blinker():
    yield
    signals = chain(*(x.signals.values()
                      for x in (workflow, util.EventHandler, handlers)))
    for signal in signals:
        signal._clear_state()

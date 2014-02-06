from itertools import chain, repeat
import xml.etree.cElementTree as ET

import mock
import pytest
import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path


@pytest.fixture
def pluginclass(mock_findinpath):
    import spreadsplug.scantailor as scantailor
    return scantailor.ScanTailorPlugin


@pytest.fixture
def config(pluginclass):
    config = confit.Configuration('test_scantailor')
    tmpl = pluginclass.configuration_template()
    for key, option in tmpl.items():
        if option.selectable:
            config['scantailor'][key] = option.value[0]
        else:
            config['scantailor'][key] = option.value
    return config


@pytest.fixture
def plugin(pluginclass, config):
    with mock.patch('subprocess.check_output') as mock_co:
        mock_co.return_value = "".join(chain(
            repeat("\n", 7),
            ("scantailor-cli [options] <images|directory|-> <output>",))
        )
        return pluginclass(config)


@mock.patch('spreadsplug.scantailor.subprocess.call')
def test_generate_configuration(call, plugin):
    # TODO: Setup up some config variables
    plugin._generate_configuration(Path('/tmp/foo.st'),
                                   Path('/tmp/raw'),
                                   Path('/tmp/out'))
    # TODO: Check the sp.call for the correct parameters


@mock.patch('spreadsplug.scantailor.subprocess.call')
def test_generate_configuration_noenhanced(call, config, pluginclass):
    # TODO: Setup up some config variables
    with mock.patch('subprocess.check_output') as mock_co:
        mock_co.return_value = "".join(chain(
            repeat("\n", 7),
            ("scantailor-cli [options] <image, image, ...>"
             " <output_directory>",))
        )
        plugin = pluginclass(config)
    imgdir = mock.MagicMock(wraps=Path('/tmp/raw'))
    imgs = [imgdir/"foo.jpg", imgdir/"bar.jpg"]
    imgdir.iterdir.return_value = imgs
    plugin._generate_configuration(Path('/tmp/foo.st'), imgdir,
                                   Path('/tmp/out'))
    assert (unicode(imgs[0]) in call.call_args[0][0])


def test_split_configuration(plugin, tmpdir):
    with mock.patch('spreadsplug.scantailor.multiprocessing.cpu_count') as cnt:
        cnt.return_value = 4
        splitfiles = plugin._split_configuration(
            Path('./tests/data/test.scanTailor'), Path(unicode(tmpdir)))
    assert len(splitfiles) == 4
    tree = ET.parse(unicode(splitfiles[0]))
    for elem in ('files', 'images', 'pages', 'file-name-disambiguation'):
        assert len(tree.find('./{0}'.format(elem))) == 7


@mock.patch('spreadsplug.scantailor.subprocess.Popen')
def test_generate_output(popen, plugin):
        plugin._split_configuration = mock.Mock(
            return_value=['foo.st', 'bar.st'])
        plugin._generate_output('/tmp/foo.st', '/tmp')


@mock.patch('spreadsplug.scantailor.subprocess.call')
def test_process(call, plugin):
    plugin._generate_configuration = mock.Mock()
    plugin._generate_output = mock.Mock()
    plugin.config['autopilot'] = True
    plugin.process(Path('/tmp'))
    assert call.call_count == 0
    plugin.config['autopilot'] = False
    plugin.process(Path('/tmp'))
    call.assert_called_with(['scantailor', '/tmp/tmp.ScanTailor'])

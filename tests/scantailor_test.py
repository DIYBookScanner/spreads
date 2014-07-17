from itertools import chain, repeat
import xml.etree.cElementTree as ET

import mock
import pytest
import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path

from spreads.workflow import Page


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
    with mock.patch('spreads.util.get_subprocess') as mock_sp:
        mock_sp.return_value.communicate.return_value = ("".join(chain(
            repeat("\n", 7),
            ("scantailor-cli [options] <images|directory|-> <output>",))),)
        return pluginclass(config)


@mock.patch('spreadsplug.scantailor.psutil.Process')
@mock.patch('spreads.util.get_subprocess')
def test_generate_configuration(get_sp, proc, plugin):
    proc.return_value.is_running.return_value = False
    in_paths = ['{0:03}.jpg'.format(idx) for idx in xrange(5)]
    proj_file = Path('/tmp/foo.st')
    out_dir = Path('/tmp/out')
    plugin._generate_configuration(in_paths, proj_file, out_dir)
    args = get_sp.call_args[0][0]
    for fp in in_paths:
        assert fp in args


def test_split_configuration(plugin, tmpdir):
    with mock.patch('spreadsplug.scantailor.multiprocessing.cpu_count') as cnt:
        cnt.return_value = 4
        splitfiles = plugin._split_configuration(
            Path('./tests/data/test.scanTailor'), Path(unicode(tmpdir)))
    assert len(splitfiles) == 4
    tree = ET.parse(unicode(splitfiles[0]))
    for elem in ('files', 'images', 'pages', 'file-name-disambiguation'):
        assert len(tree.find('./{0}'.format(elem))) == 7


@mock.patch('spreads.util.get_subprocess')
def test_generate_output(get_sp, plugin):
        plugin._split_configuration = mock.Mock(
            return_value=['foo.st', 'bar.st'])
        plugin._generate_output('/tmp/foo.st', Path('/tmp'), 8)


@mock.patch('spreads.util.get_subprocess')
def test_process(get_sp, plugin, tmpdir):
    def create_out_files(pf, out_dir, num):
        for p in pages:
            (out_dir/(p.raw_image.stem + '.tif')).touch()
    plugin._generate_configuration = mock.Mock()
    plugin._generate_output = create_out_files
    plugin.config['autopilot'] = True

    pages = [Page(Path('{0:03}.jpg'.format(idx))) for idx in xrange(5)]
    target_dir = Path(unicode(tmpdir))
    plugin.process(pages, target_dir)
    assert get_sp.call_count == 0
    for p in pages:
        assert 'scantailor' in p.processed_images
        assert p.processed_images['scantailor'].parent == target_dir
        assert p.processed_images['scantailor'].exists()

    plugin.config['autopilot'] = False
    with mock.patch('time.sleep'):
        plugin.process(pages, target_dir)
    assert get_sp.call_count == 1

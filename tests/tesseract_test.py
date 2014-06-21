import re
import shutil
import time
import xml.etree.cElementTree as ET

import mock
import pytest
import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path

from spreads.workflow import Page


@pytest.fixture
def pluginclass(mock_findinpath):
    with mock.patch('subprocess.check_output') as co:
        co.return_value = "x\ndeu\nfra\neng\nx"
        import spreadsplug.tesseract as tesseract
        return tesseract.TesseractPlugin


@pytest.fixture
def config(pluginclass):
    config = confit.Configuration('test_tesseract')
    tmpl = pluginclass.configuration_template()
    for key, option in tmpl.items():
        if option.selectable:
            config['tesseract'][key] = option.value[0]
        else:
            config['tesseract'][key] = option.value
    return config


@pytest.fixture
def plugin(pluginclass, config):
    return pluginclass(config)


def test_perform_ocr(plugin, tmpdir):
    def dummy_poll():
        time.sleep(0.5)
        return True

    def dummy_popen(args, stderr, stdout):
        if int(Path(args[2]).stem) % 2:
            shutil.copyfile('./tests/data/001.hocr', args[2]+'.html')
        else:
            shutil.copyfile('./tests/data/000.hocr', args[2]+'.html')
        return mock.Mock(side_effect=dummy_poll)
    in_paths = [Path('{0:03}.tif'.format(idx)) for idx in xrange(10)]
    with mock.patch('spreadsplug.tesseract.subprocess.Popen') as popen:
        popen.side_effect = dummy_popen
        plugin._perform_ocr(in_paths, tmpdir, 'eng')
    for img in in_paths:
        assert tmpdir.join(img.stem + '.html').exists()


def test_fix_hocr(plugin, tmpdir):
    shutil.copyfile('./tests/data/000.hocr', unicode(tmpdir.join('test.html')))
    fpath = Path(unicode(tmpdir.join('test.html')))
    plugin._fix_hocr(fpath)
    with fpath.open('r') as fp:
        matches = re.findall(
            r'(<span[^>]*>(<strong>)? +(</strong>)?</span> *){2}',
            fp.read())
    assert len(matches) == 0


def test_output(plugin, tmpdir):
    dummy_pages = []
    for idx in xrange(20):
        dummy_pages.append(
            Page(Path('000.jpg'), idx,
                 processed_images={'tesseract': Path('./tests/data/000.hocr')})
        )
    plugin.output(dummy_pages, tmpdir, None, None)
    assert tmpdir.join('text.html').exists()
    tree = ET.parse(unicode(tmpdir.join('text.html')))
    assert len(tree.findall('.//span[@class="ocrx_word"]')) == 20*201
    assert len(tree.findall('.//span[@class="ocr_line"]')) == 20*26
    assert len(tree.findall('.//p[@class="ocr_par"]')) == 20*4
    assert len(tree.findall('.//div[@class="ocr_page"]')) == 20

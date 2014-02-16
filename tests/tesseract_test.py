import re
import shutil
import time
import xml.etree.cElementTree as ET

import mock
import pytest
import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path


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
        return mock.Mock(side_effect=dummy_poll)
    imgdir = tmpdir.join('/done')
    imgdir.mkdir()
    for i in xrange(10):
        imgdir.join('{0:03}.tif'.format(i)).write('')
    with mock.patch('spreadsplug.tesseract.subprocess.Popen') as popen:
        popen.side_effect = dummy_popen
        plugin._perform_ocr(Path(unicode(imgdir)), 'eng')
    for img in (x for x in imgdir.listdir() if x.ext == 'tif'):
        assert imgdir.join(img.purebasename + 'html').exists()


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
    basedir = tmpdir.join('test')
    basedir.mkdir()
    basedir.join('out').mkdir()
    done_path = basedir.join('done')
    done_path.mkdir()
    for idx in xrange(20):
        shutil.copyfile('./tests/data/000.hocr',
                        unicode(done_path.join('{0:03}.html'.format(idx))))
    fpath = Path(unicode(basedir))
    plugin.output(fpath)
    assert basedir.join('out', 'test.hocr').exists()
    tree = ET.parse(unicode(basedir.join('out', 'test.hocr')))
    assert len(tree.findall('.//span[@class="ocrx_word"]')) == 20*201
    assert len(tree.findall('.//span[@class="ocr_line"]')) == 20*26
    assert len(tree.findall('.//p[@class="ocr_par"]')) == 20*4
    assert len(tree.findall('.//div[@class="ocr_page"]')) == 20

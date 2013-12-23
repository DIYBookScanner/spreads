import unittest
from itertools import chain, repeat

import spreads.vendor.confit as confit
from mock import MagicMock as Mock, patch
from spreads.vendor.pathlib import Path

import spreads.plugin as plugin

with patch('subprocess.check_output') as mock_co:
    mock_co.return_value = "".join(chain(
        repeat("\n", 7),
        ("scantailor-cli [options] <images|directory|-> <output>",))
    )
    import spreadsplug.scantailor as scantailor


class TestScanTailor(unittest.TestCase):
    @patch('subprocess.check_output')
    def setUp(self, mock_co):
        self.config = confit.Configuration('test_scantailor')

        tmpl = scantailor.ScanTailorPlugin.configuration_template()
        for key, option in tmpl.items():
            if option.selectable:
                self.config['scantailor'][key] = option.value[0]
            else:
                self.config['scantailor'][key] = option.value
        self.stplug = scantailor.ScanTailorPlugin(self.config)

    def tearDown(self):
        plugin.SpreadsNamedExtensionManager._instance = None

    def test_generate_configuration(self):
        scantailor.subprocess.call = Mock()
        assert self.stplug._enhanced
        # TODO: Setup up some config variables
        self.stplug._generate_configuration(Path('/tmp/foo.st'),
                                            Path('/tmp/raw'),
                                            Path('/tmp/out'))
        # TODO: Check the sp.call for the correct parameters

    def test_generate_configuration_noenhanced(self):
        scantailor.subprocess.call = Mock()
        # TODO: Setup up some config variables
        self.stplug._enhanced = False
        imgdir_mock = Mock(wraps=Path('/tmp/raw'))
        mock_imgs = [imgdir_mock/"foo.jpg", imgdir_mock/"bar.jpg"]
        imgdir_mock.iterdir.return_value = mock_imgs
        self.stplug._generate_configuration(Path('/tmp/foo.st'), imgdir_mock,
                                            Path('/tmp/out'))
        assert (unicode(mock_imgs[0])
                in scantailor.subprocess.call.call_args[0][0])

    def test_split_configuration(self):
        # TODO: Provide a sample configuration
        # TODO: Check for number of files
        # TODO: Check if the files have all the pages
        pass

    def test_generate_output(self):
        scantailor.subprocess.Popen = Mock()
        self.stplug._split_configuration = Mock()
        self.stplug._generate_output('/tmp/foo.st', '/tmp')

    def test_process(self):
        scantailor.subprocess.call = Mock()
        self.stplug._generate_configuration = Mock()
        self.stplug._generate_output = Mock()
        self.stplug.config['autopilot'] = True
        self.stplug.process(Path('/tmp'))
        assert scantailor.subprocess.call.call_count == 0
        self.stplug.config['autopilot'] = False
        self.stplug.process(Path('/tmp'))
        scantailor.subprocess.call.assert_called_with(
            ['scantailor', '/tmp/tmp.ScanTailor'])

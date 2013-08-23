from mock import MagicMock as Mock

import spreads
import spreadsplug.scantailor as scantailor

class TestScanTailor(object):
    def setUp(self):
        spreads.config.clear()
        spreads.config.read(user=False)
        self.stplug = scantailor.ScanTailorPlugin(spreads.config)

    def test_generate_configuration(self):
        scantailor.subprocess.call = Mock()
        # TODO: Setup up some config variables
        self.stplug._generate_configuration('/tmp/foo.st', '/tmp/raw',
                                            '/tmp/out')
        # TODO: Check the sp.call for the correct parameters

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
        spreads.config['autopilot'] = True
        self.stplug.process('/tmp')
        assert scantailor.subprocess.call.call_count == 0
        spreads.config['autopilot'] = False
        self.stplug.process('/tmp')
        scantailor.subprocess.call.assert_called_with(
            ['scantailor', '/tmp/tmp.ScanTailor'])

import time

import PySide.QtTest as QtTest
from PySide.QtGui import QPixmap, QImage, QApplication
from mock import patch, MagicMock as Mock

import spreads
import spreads.plugin as plugin
import spreadsplug.gui.gui as gui


class TestWizard(object):
    def setUp(self):
        try:
            self.app = QApplication([])
        except RuntimeError:
            # TODO: Somehow our app gets created multiple times, so we just
            #       ignore that here...
            pass
        spreads.config.clear()
        spreads.config.read(user=False)
        spreads.config['plugins'] = (spreads.config['plugins'].get()
                                     + [u'tesseract'])
        print spreads.config['plugins']
        print "Setting up plugin configuration"
        plugin.setup_plugin_config()

        # TODO: Cams ought to be 'left' and 'right'!
        self.cams = [Mock(), Mock()]
        gui.get_devices = Mock(return_value=self.cams)
        # Mock out message boxes
        gui.QtGui.QMessageBox = Mock()
        gui.QtGui.QMessageBox.exec_.return_value = True
        self.wizard = gui.SpreadsWizard(spreads.config, self.cams)
        self.wizard.show()

    def tearDown(self):
        gui.QtGui.QImage = QImage
        gui.QtGui.QPixmap = QPixmap

    def test_intro_page(self):
        page = self.wizard.page(0)
        page.initializePage()
        page.line_edit.setText('/tmp/foobar')
        assert page.validatePage()
        assert self.wizard.project_path == '/tmp/foobar'
        assert not spreads.config['keep'].get(bool)
        #assert spreads.config['first_page'].get(unicode) == "left"
        #assert not spreads.config['rotate_inverse'].get(bool)
        #assert not spreads.config['autopilot'].get(bool)
        assert (spreads.config['scantailor']['detection'].get(unicode)
                == u"content")
        #assert spreads.config['language'].get(str) == 'eng'

        # TODO: Check option boxes
        # TODO: Select path
        # TODO: Assert that spreads.config is updated accordingly
        # TODO: Assert that the project path is set correctly

    def test_intro_page_nopath(self):
        page = self.wizard.page(0)
        page.initializePage()
        assert not page.validatePage()

    def test_connect_page_nocams(self):
        # TODO: Write me!
        pass

    def test_capture_page(self):
        self.wizard.selected_devices = self.cams
        gui.QtGui.QImage = Mock()
        gui.QtGui.QPixmap.fromImage = Mock(return_value=QPixmap())
        page = self.wizard.page(1)
        page.initializePage()
        # TODO: Test capture triggering, logbox updates, etc
        assert page.validatePage()

    @patch('os.listdir')
    def test_download_page(self, listdir):
        #spreads.config['keep'] = False
        #spreads.config['parallel_download'] = True
        listdir.return_value = True
        self.wizard.selected_devices = self.cams
        self.wizard.project_path = '/tmp/foo'
        gui.workflow = Mock()
        gui.workflow.download.side_effect = lambda x, y: time.sleep(1)
        gui.os.listdir = listdir
        page = self.wizard.page(2)
        page.initializePage()
        page.doDownload()
        # TODO: See that logbox works, donwload is executed, warning is
        #       emitted on combine failure
        assert page.validatePage()

    def test_postprocess_page(self):
        page = self.wizard.page(3)
        page.initializePage()
        # TODO: See that logbox works, postprocess is executed, warning is
        #       emitted on combine failure
        assert page.validatePage()

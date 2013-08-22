import PySide.QtTest as QtTest
from PySide.QtGui import QPixmap, QImage, QApplication
from mock import MagicMock as Mock

import spreads
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
        # TODO: Cams ought to be 'left' and 'right'!
        self.cams = [Mock(), Mock()]
        gui.get_devices = Mock(return_value=self.cams)
        # Mock out message boxes
        gui.QtGui.QMessageBox = Mock()
        gui.QtGui.QMessageBox.exec_.return_value = True
        self.wizard = gui.SpreadsWizard(spreads.config)
        self.wizard.show()

    def tearDown(self):
        gui.QtGui.QImage = QImage
        gui.QtGui.QPixmap =QPixmap

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
        assert not spreads.config['page_detection'].get(bool)
        #assert spreads.config['language'].get(str) == 'eng'

        # TODO: Check option boxes
        # TODO: Select path
        # TODO: Assert that spreads.config is updated accordingly
        # TODO: Assert that the project path is set correctly

    def test_intro_page_nopath(self):
        page = self.wizard.page(0)
        page.initializePage()
        assert not page.validatePage()

    def test_connect_page(self):
        page = self.wizard.page(1)
        page.initializePage()
        assert page.validatePage()
        assert self.wizard.selected_devices == self.cams
        for cam in self.cams:
            assert cam.prepare_capture.call_count == 1

    def test_connect_page_nocams(self):
        # TODO: Write me!
        pass

    def test_capture_page(self):
        self.wizard.selected_devices = self.cams
        gui.QtGui.QImage = Mock()
        gui.QtGui.QPixmap.fromImage = Mock(return_value = QPixmap())
        page = self.wizard.page(2)
        page.initializePage()
        # TODO: Test capture triggering, logbox updates, etc
        assert page.validatePage()

    def test_download_page(self):
        self.wizard.selected_devices = self.cams
        page = self.wizard.page(3)
        page.initializePage()
        # TODO: See that logbox works, donwload is executed, warning is
        #       emitted on combine failure
        assert page.validatePage()

    def test_postprocess_page(self):
        page = self.wizard.page(4)
        page.initializePage()
        # TODO: See that logbox works, postprocess is executed, warning is
        #       emitted on combine failure
        assert page.validatePage()

    def test_postprocess_page(self):
        page = self.wizard.page(4)
        page.initializePage()
        # TODO: See that logbox works, donwload is executed, warning is
        #       emitted on combine failure
        assert page.validatePage()

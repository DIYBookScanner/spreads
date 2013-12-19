from PySide.QtGui import QPixmap, QImage, QApplication
from mock import patch, MagicMock as Mock

import spreads.confit as confit
import spreads.plugin as plugin
import spreads.workflow as workflow
import spreadsplug.gui.gui as gui
with patch('subprocess.check_output'):
    import spreadsplug.tesseract as tess


class TestWizard(object):
    def setUp(self):
        try:
            self.app = QApplication([])
        except RuntimeError:
            # TODO: Somehow our app gets created multiple times, so we just
            #       ignore that here...
            pass
        self.config = confit.Configuration('test_gui')
        self.config['plugins'] = [u'tesseract', u'scantailor']
        self.config['driver'] = u'dummy'
        self.workflow = workflow.Workflow(config=self.config,
                                          path='/tmp/foobar')
        plugin.setup_plugin_config(self.config)

        tess.AVAILABLE_LANGS = ["en"]
        # TODO: Cams ought to be 'odd' and 'even'!
        self.cams = [Mock(), Mock()]
        workflow.get_devices = Mock(return_value=self.cams)
        # Mock out message boxes
        gui.QtGui.QMessageBox = Mock()
        gui.QtGui.QMessageBox.exec_.return_value = True
        self.wizard = gui.SpreadsWizard(self.config)
        self.wizard.show()

    def tearDown(self):
        gui.QtGui.QImage = QImage
        gui.QtGui.QPixmap = QPixmap

    def test_intro_page(self):
        page = self.wizard.page(0)
        page.initializePage()
        page.line_edit.setText('/tmp/foobar')
        assert page.validatePage()
        assert self.wizard.workflow.path == '/tmp/foobar'
        assert self.config['parallel_capture'].get(bool)
        assert not self.config['flip_target_pages'].get(bool)
        #assert spreads.config['first_page'].get(unicode) == "left"
        #assert not spreads.config['rotate_inverse'].get(bool)
        #assert not spreads.config['autopilot'].get(bool)
        assert (self.config['scantailor']['detection'].get(unicode)
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

    def test_capture_page(self):
        self.wizard.workflow = self.workflow
        self.wizard.selected_devices = self.cams
        gui.QtGui.QImage = Mock()
        gui.QtGui.QPixmap.fromImage = Mock(return_value=QPixmap())
        page = self.wizard.page(1)
        page.initializePage()
        # TODO: Test capture triggering, logbox updates, etc
        assert page.validatePage()

    def test_postprocess_page(self):
        self.wizard.workflow = self.workflow
        page = self.wizard.page(3)
        page.initializePage()
        # TODO: See that logbox works, postprocess is executed
        assert page.validatePage()

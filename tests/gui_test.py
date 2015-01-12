import mock
import pytest
pytestmark = pytest.mark.guitest


@pytest.yield_fixture
def mock_msgbox():
    with mock.patch('spreadsplug.gui.gui.QtGui.QMessageBox') as msgbox:
        msgbox.exec_.return_value = True
        yield msgbox


@pytest.fixture
def wizard(config):
    import spreadsplug.gui.gui as gui
    wizard = gui.SpreadsWizard(config)
    wizard.show()
    return wizard


@pytest.fixture
def workflow(config, tmpdir):
    from spreads.workflow import Workflow
    wf = Workflow(path=unicode(tmpdir), config=config)
    return wf


def test_intro_page(wizard, tmpdir):
    page = wizard.page(0)
    page.initializePage()
    page.line_edit.setText(unicode(tmpdir))
    assert 'device' in page.plugin_widgets
    assert page.validatePage()
    assert unicode(wizard.workflow.path) == unicode(tmpdir)
    # TODO: Check plugin options


def test_intro_page_nopath(wizard, mock_msgbox):
    page = wizard.page(0)
    page.initializePage()
    assert not page.validatePage()


def test_capture_page(wizard, workflow):
    wizard.workflow = workflow
    with mock.patch.multiple("spreadsplug.gui.gui.QtGui", QImage=mock.DEFAULT,
                             QPixmap=mock.DEFAULT) as values:
        values["QPixmap"].fromImage = mock.Mock(
            return_value=values["QImage"]())
        page = wizard.page(1)
        page.initializePage()
        # TODO: Test capture triggering, logbox updates, etc
        assert page.validatePage()


def test_postprocess_page(wizard, workflow):
    wizard.workflow = workflow
    page = wizard.page(2)
    page.initializePage()
    # TODO: See that logbox works, postprocess is executed
    assert page.validatePage()


def test_output_page(wizard, workflow):
    wizard.workflow = workflow
    page = wizard.page(3)
    page.initializePage()
    # TODO: See that logbox works, postprocess is executed
    assert page.validatePage()

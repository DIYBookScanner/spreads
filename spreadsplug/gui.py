import sys

from PySide import QtCore, QtGui

import spreads
import spreads.commands as cmd
import spreads.util as util
from spreads.plugin import HookPlugin


class GuiCommand(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        guiparser = rootparser.add_parser(
            'gui', help="Start the GUI wizard")
        guiparser.set_defaults(func=wizard)


class SpreadsWizard(QtGui.QWizard):
    def __init__(self, config, parent=None):
        super(SpreadsWizard, self).__init__(parent)

        self.addPage(IntroPage(config))
        self.addPage(SettingsPage(config))
        self.addPage(ConnectPage(config))
        self.addPage(ConfigurePage(config))
        self.addPage(PreviewPage(config))
        self.addPage(CapturePage(config))
        self.addPage(DownloadPage(config))
        self.addPage(PostprocessPage(config))
        self.addPage(FinishPage(config))

        button_layout = []
        button_layout.append(QtGui.QWizard.BackButton)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.CustomButton1)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.NextButton)
        self.setButtonLayout(button_layout)

        self.setButtonText(QtGui.QWizard.CustomButton1, "Settings")

        self.setWindowTitle("Spreads Wizard")


class IntroPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle("Welcome")


class SettingsPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(SettingsPage, self).__init__(parent)

        self.setTitle("Settings")


class ConnectPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(ConnectPage, self).__init__(parent)

        self.setTitle("Connect")


class ConfigurePage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(ConfigurePage, self).__init__(parent)

        self.setTitle("Configure devices")


class PreviewPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PreviewPage, self).__init__(parent)

        self.setTitle("Device preview")


class CapturePage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(CapturePage, self).__init__(parent)

        self.setTitle("Capture")


class DownloadPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(DownloadPage, self).__init__(parent)

        self.setTitle("Download")


class PostprocessPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PostprocessPage, self).__init__(parent)

        self.setTitle("Postprocessing")


class FinishPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(FinishPage, self).__init__(parent)

        self.setTitle("Done!")


def wizard(args):
    app = QtGui.QApplication(sys.argv)
    wizard = SpreadsWizard(spreads.config)
    wizard.show()
    wizard.exec_()

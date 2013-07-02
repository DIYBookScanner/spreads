from PySide import QtGui

import spreads.commands as cmd
import spreads.util as util

import gui_rc


class SpreadsWizard(QtGui.QWizard):
    def __init__(self, config, parent=None):
        super(SpreadsWizard, self).__init__(parent)

        self.addPage(IntroPage(config))
        self.addPage(ConnectPage(config))
        self.addPage(ConfigurePage(config))
        self.addPage(PreviewPage(config))
        self.addPage(CapturePage(config))
        self.addPage(PostprocessPage(config))
        self.addPage(FinishPage(config))

        self.setPixmap(QtGui.QWizard.WatermarkPixmap,
                       QtGui.QPixmap(':/pixmaps/monk.png'))

        button_layout = []
        button_layout.append(QtGui.QWizard.BackButton)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.CustomButton1)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.NextButton)
        button_layout.append(QtGui.QWizard.FinishButton)
        self.setButtonLayout(button_layout)

        self.setButtonText(QtGui.QWizard.CustomButton1, "Settings")

        self.setWindowTitle("Spreads Wizard")


class IntroPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(IntroPage, self).__init__(parent)
        self.setTitle("Welcome!")

        intro_label = QtGui.QLabel(
            "This wizard will guide you through the digitization workflow. "
        )

        # TODO: Add signal to browse_btn that calls QFileDialog and updates
        #       line_edit.
        dirpick_label = QtGui.QLabel("Please select a project directory.")
        dirpick_layout = QtGui.QHBoxLayout()
        self.line_edit = QtGui.QLineEdit()
        browse_btn = QtGui.QPushButton("Browse")
        dirpick_layout.addWidget(self.line_edit)
        dirpick_layout.addWidget(browse_btn)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addSpacing(30)
        layout.addWidget(dirpick_label)
        layout.addLayout(dirpick_layout)
        self.setLayout(layout)


class SettingsPage(QtGui.QWizardPage):
    # TODO: This shouldn't be a widget page, but a separate window
    def __init__(self, config, parent=None):
        super(SettingsPage, self).__init__(parent)

        self.setTitle("Settings")


class ConnectPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(ConnectPage, self).__init__(parent)
        # TODO: Show an activity indicator while get_devices() is running,
        #       use QtGui.QProgressDialog, with .setRange(0,0) for
        #       indeterminate time

        self.setTitle("Connect")

        # TODO: Get this via get_devices()
        devices = []
        if not devices:
            label = QtGui.QLabel("<font color=red>No devices found!</font>")
        else:
            label = QtGui.QLabel("Please select one or more devices:")
        devicewidget = QtGui.QListWidget()
        devicewidget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        for device in devices:
            devicewidget.setCurrentItem(QtGui.QListWidgetItem(device,
                                                              devicewidget))

        # TODO: Trigger signal to run get_devices() again and refresh label
        #       and devicewidget
        refresh_btn = QtGui.QPushButton("Refresh")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(devicewidget)
        layout.addWidget(refresh_btn)
        self.setLayout(layout)


class ConfigurePage(QtGui.QWizardPage):
    # TODO: This should only be viewed if the devices have not yet been
    #       configured
    def __init__(self, config, parent=None):
        super(ConfigurePage, self).__init__(parent)

        self.setTitle("Configure devices")


class PreviewPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PreviewPage, self).__init__(parent)
        # TODO: Get viewport from devices, construct QImage from it
        # TODO: Display the Qimages in two label widgets that are refreshed
        #       at 10fps or so. Format from pyptpchdk is wand.Image with RGB32,
        #       should be fine.

        self.setTitle("Device preview")

        label = QtGui.QLabel("Please check if your cameras are well adjusted:")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class CapturePage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(CapturePage, self).__init__(parent)

        self.setTitle("Capturing from devices")


class DownloadPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(DownloadPage, self).__init__(parent)
        # TODO: This shouldn't be a wizard page, but merely a progress
        #       dialog!
        # TODO: Change DevicePlugin API to make download_all_files an
        #       iterator with __len__, so we can display a nice progress bar.

        self.setTitle("Download")


class PostprocessPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PostprocessPage, self).__init__(parent)
        # TODO: Show textarea with logging.info
        self.setTitle("Postprocessing")


class FinishPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(FinishPage, self).__init__(parent)
        
        self.setFinalPage(True)
        self.setTitle("Done!")

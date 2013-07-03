from PySide import QtCore, QtGui

import spreads.commands as cmd
import spreads.util as util

import gui_rc


class SpreadsWizard(QtGui.QWizard):
    def __init__(self, config, parent=None):
        super(SpreadsWizard, self).__init__(parent)

        self.addPage(IntroPage(config))
        self.addPage(ConnectPage(config))
        self.addPage(PreviewPage(config))
        self.addPage(CapturePage(config))
        self.addPage(PostprocessPage(config))
        self.addPage(FinishPage(config))

        self.setPixmap(QtGui.QWizard.WatermarkPixmap,
                       QtGui.QPixmap(':/pixmaps/monk.png'))

        button_layout = []
        button_layout.append(QtGui.QWizard.BackButton)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.CancelButton)
        button_layout.append(QtGui.QWizard.Stretch)
        button_layout.append(QtGui.QWizard.NextButton)
        button_layout.append(QtGui.QWizard.FinishButton)
        self.setButtonLayout(button_layout)

        self.setWindowTitle("Spreads Wizard")


class IntroPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(IntroPage, self).__init__(parent)
        self.setTitle("Welcome!")

        intro_label = QtGui.QLabel(
            "This wizard will guide you through the digitization workflow. "
        )

        dirpick_label = QtGui.QLabel("Please select a project directory.")
        dirpick_layout = QtGui.QHBoxLayout()
        self.line_edit = QtGui.QLineEdit()
        browse_btn = QtGui.QPushButton("Browse")
        dirpick_layout.addWidget(self.line_edit)
        dirpick_layout.addWidget(browse_btn)

        browse_btn.clicked.connect(self.show_filepicker)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addSpacing(30)
        layout.addWidget(dirpick_label)
        layout.addLayout(dirpick_layout)
        self.setLayout(layout)

    def show_filepicker(self):
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly, True)
        dialog.exec_()
        self.line_edit.setText(dialog.selectedFiles()[0])


class ConnectPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(ConnectPage, self).__init__(parent)
        # TODO: Show an activity indicator while get_devices() is running,
        #       use QtGui.QProgressDialog, with .setRange(0,0) for
        #       indeterminate time

        self.setTitle("Connect")

        self.label = QtGui.QLabel("Detecting devices...")
        self.devicewidget = QtGui.QListWidget()
        self.devicewidget.setSelectionMode(QtGui.QAbstractItemView
                                           .MultiSelection)

        self.update_devices()
        refresh_btn = QtGui.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_devices)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.devicewidget)
        layout.addWidget(refresh_btn)
        self.setLayout(layout)

    def update_devices(self):
        # TODO: Use some kind of activity indicator to keep users from
        #       becoming impatient
        self.devicewidget.clear()
        self.label.setText("Detecting devices...")
        devices = ["Camera A", "Camera B"]
        if not devices:
            self.label.setText("<font color=red>No devices found!</font>")
        else:
            self.label.setText("Please select one or more devices:")
        for device in devices:
            self.devicewidget.setCurrentItem(
                QtGui.QListWidgetItem(device,
                                      self.devicewidget))


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
        self.setTitle("Postprocessing")

        # TODO: Update logbox from logging.info
        self.logbox = QtGui.QTextEdit()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.logbox)
        self.setLayout(layout)


class FinishPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(FinishPage, self).__init__(parent)

        self.setFinalPage(True)
        self.setTitle("Done!")

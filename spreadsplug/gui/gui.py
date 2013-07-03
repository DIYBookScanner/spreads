import time

from concurrent.futures import ThreadPoolExecutor 
from PySide import QtCore, QtGui

import spreads.commands as cmd
import spreads.util as util
from spreads.plugin import get_devices

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

    def validatePage(self):
        self.wizard().project_path = self.line_edit.text()
        if not self.wizard().project_path:
            msg_box = QtGui.QMessageBox()
            msg_box.setText("Please select a project directory.")
            msg_box.setIcon(QtGui.QMessageBox.Critical)
            msg_box.exec_()
            return False
        return True


class ConnectPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(ConnectPage, self).__init__(parent)
        # TODO: Show an activity indicator while get_devices() is running,
        #       use QtGui.QProgressDialog, with .setRange(0,0) for
        #       indeterminate time

        self.setTitle("Connect")

    def initializePage(self):
        self.progress = QtGui.QProgressDialog("Detecting devices...",
                                              "Cancel", 0, 0, self)

        self.label = QtGui.QLabel("Detecting devices...")
        self.devicewidget = QtGui.QListWidget()
        self.devicewidget.setSelectionMode(QtGui.QAbstractItemView
                                           .MultiSelection)

        refresh_btn = QtGui.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_devices)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.devicewidget)
        layout.addWidget(refresh_btn)
        self.setLayout(layout)

        self.update_devices()

    def update_devices(self):
        self.devicewidget.clear()
        self.label.setText("Detecting devices...")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_devices)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progress.setValue(1)
                time.sleep(0.001)
            try:
                devices = future.result()
            except util.DeviceException:
                devices = []
        self.progress.close()
        if not devices:
            self.label.setText("<font color=red>No devices found!</font>")
        else:
            self.label.setText("Please select one or more devices:")
        self.devices = []
        for idx, device in enumerate(devices, 1000):
            self.devicewidget.setCurrentItem(
                QtGui.QListWidgetItem(device.__class__.__name__,
                                      self.devicewidget, type=idx))
            self.devices.append(device)

    def nextId(self):
        self.wizard().selected_devices = [self.devices[x.type()-1000]
                                          for x
                                          in self.devicewidget.selectedItems()]
        if any([not x.orientation for x in self.wizard().selected_devices]):
            return super(ConnectPage, self).nextId()
        return super(ConnectPage, self).nextId()+1

    def validatePage(self):
        if not self.wizard().selected_devices:
            msg_box = QtGui.QMessageBox()
            msg_box.setText("No device selected.")
            msg_box.setIcon(QtGui.QMessageBox.Critical)
            msg_box.exec_()
            return False
        return True


class ConfigurePage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Configure devices")
        devices = [x for x in self.wizard().selected_devices
                   if not x.orientation]
        if len(devices) > 1:
            orientation = "left"
        else:
            orientation = "right"
        label = QtGui.QLabel("Please connect the {0} device."
                             .format(orientation))
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

    def nextId(self):
        if any([not x.orientation for x in self.wizard().selected_devices]):
            return super(ConnectPage, self).nextId()-1
        return super(ConnectPage, self).nextId()


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

    def validatePage(self):
        def download_images():
            time.sleep(2)
        #TODO: Display a real progress bar here, update it according to the
        #      combined number of files in raw or its subfolders
        progress = QtGui.QProgressDialog("Downloading files...",
                                         "Cancel", 0, 0, self)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(download_images)
            while not future.done():
                QtGui.qApp.processEvents()
                progress.setValue(1)
                time.sleep(0.001)
        progress.close()
        return True


class PostprocessPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PostprocessPage, self).__init__(parent)
        self.setTitle("Postprocessing")
        # TODO: Make postprocess() a generator and update progress according
        #       to it.
        # TODO: Update logbox from logging.info
        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, 0)
        self.progressbar.setAlignment(QtCore.Qt.AlignCenter)
        self.logbox = QtGui.QTextEdit()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.progressbar)
        layout.addWidget(self.logbox)
        self.setLayout(layout)


class FinishPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(FinishPage, self).__init__(parent)
        self.setFinalPage(True)
        self.setTitle("Done!")
        # TODO: Offer option to view project folder on exit

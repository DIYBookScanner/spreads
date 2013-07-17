import logging
import time

from concurrent.futures import ThreadPoolExecutor
from PySide import QtCore, QtGui
from PIL import Image

import spreads.workflow as workflow
import spreads.util as util
from spreads.plugin import get_devices

import gui_rc


class LogBoxHandler(logging.Handler):
    # NOTE: This is neccessary, because a signal has to be an attribute of
    #       a QObject instance. Multiple inheritance does not work here,
    #       as both logging.Handler and QObject have an "emit" method
    class DummyQObject(QtCore.QObject):
        sig = QtCore.Signal(unicode)

    def __init__(self, textedit):
        logging.Handler.__init__(self)
        self._qobj = self.DummyQObject()
        self.sig = self._qobj.sig
        self.textedit = textedit

    def emit(self, record):
        self.sig.emit(self.format(record))


class LogBoxFormatter(logging.Formatter):
    LEVELS = {
        'ERROR': "<strong><font color=\"red\">{0}</font></strong>",
        'CRITICAL': "<strong><font color=\"orange\">{0}</font></strong>",
        'WARNING': "<strong><font color=\"orange\">{0}</font></strong>",
        'INFO': "{0}",
        'DEBUG': "{0}",
    }

    def format(self, record):
        levelname = record.levelname
        return self.LEVELS[levelname].format(record.message)


class SpreadsWizard(QtGui.QWizard):
    def __init__(self, config, parent=None):
        super(SpreadsWizard, self).__init__(parent)
        self.addPage(IntroPage(config))
        self.addPage(ConnectPage(config))
        self.addPage(ConfigurePage(config))
        self.addPage(CapturePage(config))
        self.addPage(PostprocessPage(config))
        self.addPage(OutputPage(config))
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

    def initializePage(self):
        self.update_devices()

    def update_devices(self):
        self.progress = QtGui.QProgressDialog("Detecting devices...",
                                              "Cancel", 0, 0, self)
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
        try:
            if any([not x.orientation
                    for x in self.wizard().selected_devices]):
                return super(ConnectPage, self).nextId()
        except AttributeError:
            pass
        return super(ConnectPage, self).nextId()+1

    def validatePage(self):
        self.wizard().selected_devices = [self.devices[x.type()-1000]
                                          for x
                                          in self.devicewidget.selectedItems()]
        if len(self.wizard().selected_devices) in (1, 2):
            print len(self.wizard().selected_devices)
            workflow.prepare_capture(self.wizard().selected_devices)
            return True
        msg_box = QtGui.QMessageBox()
        msg_box.setIcon(QtGui.QMessageBox.Critical)
        if len(self.wizard().selected_devices) > 2:
            msg_box.setText("Please don't select more than two devices!")
        elif not self.wizard().selected_devices:
            msg_box.setText("No device selected.")
        msg_box.exec_()
        return False


class ConfigurePage(QtGui.QWizardPage):
    # TODO: Meeeeeh, this is a bit more finicky... First, erase the devices,
    #       then connect one after the other, then connect and register both,
    #       what a PITA :3
    def __init__(self, config, parent=None):
        super(ConfigurePage, self).__init__(parent)
        self.config = config

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


class CapturePage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(CapturePage, self).__init__(parent)
        self.setTitle("Capturing from devices")
        self.start_time = None
        self.shot_count = None

        layout = QtGui.QVBoxLayout(self)
        self.status = QtGui.QLabel("Press a capture key (default: Space, B)"
                                   " to begin capturing.")

        previewbox = QtGui.QHBoxLayout()
        self.left_preview = QtGui.QLabel()
        self.right_preview = QtGui.QLabel()
        previewbox.addWidget(self.left_preview)
        previewbox.addWidget(self.right_preview)

        refresh_btn = QtGui.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_preview)

        capture_btn = QtGui.QPushButton("Capture")
        capture_btn.clicked.connect(self.doCapture)
        layout.addWidget(self.status)
        layout.addWidget(refresh_btn)
        layout.addLayout(previewbox)
        layout.addWidget(capture_btn)
        self.setLayout(layout)

    def initializePage(self):
        time.sleep(0.5)
        self.update_preview()

    def validatePage(self):
        workflow.finish_capture(self.wizard().selected_devices)
        #TODO: Display a real progress bar here, update it according to the
        #      combined number of files in raw or its subfolders
        progress = QtGui.QProgressDialog("Downloading files...",
                                         "Cancel", 0, 0, self)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.download,
                                     self.wizard().selected_devices,
                                     self.wizard().project_path)
            while future.running():
                QtGui.qApp.processEvents()
                progress.setValue(1)
                time.sleep(0.001)
        progress.close()
        return True

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_B, QtCore.Qt.Key_Space):
            self.doCapture()

    def doCapture(self):
        if self.start_time is None:
            self.start_time = time.time()
        if self.shot_count is None:
            self.shot_count = 0
        workflow.capture(self.wizard().selected_devices)
        self.update_preview()
        self.shot_count += 2
        self.status.setText("Shot {0} pages in {1:.0f} minutes "
                            "({2:.0f} pages/hour)".format(
                                self.shot_count,
                                (time.time() - self.start_time) / 60,
                                ((3600 / (time.time() - self.start_time))
                                 * self.shot_count)))

    def update_preview(self):
        def get_preview(dev):
            img = dev._device.get_preview_image()
            img = img.resize((320, 240), Image.ANTIALIAS).convert('RGBA')
            data = img.tostring('raw')
            image = QtGui.QImage(data, img.size[0], img.size[1],
                                 QtGui.QImage.Format_ARGB32).rgbSwapped()
            return dev.orientation, image

        # TODO: Auto-refreh at 5fps
        # TODO: Don't go via PIL, find a way to use RGB data directly
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = executor.map(get_preview,
                                   self.wizard().selected_devices)
            previews = tuple(futures)
        for orientation, image in previews:
            pixmap = QtGui.QPixmap.fromImage(image)
            if orientation == 'left':
                self.left_preview.setPixmap(pixmap)
            else:
                self.right_preview.setPixmap(pixmap)


class PostprocessPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(PostprocessPage, self).__init__(parent)
        self.setTitle("Postprocessing")

        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, 0)
        self.progressbar.setAlignment(QtCore.Qt.AlignCenter)
        self.logbox = QtGui.QTextEdit()
        self.log_handler = LogBoxHandler(self.logbox)
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.setFormatter(LogBoxFormatter())
        logging.getLogger().addHandler(self.log_handler)
        self.log_handler.sig.connect(self.logbox.append)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.progressbar)
        layout.addWidget(self.logbox)
        self.setLayout(layout)

    def initializePage(self):
        QtCore.QTimer.singleShot(0, self.doPostprocess)

    def doPostprocess(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.process,
                                     self.wizard().project_path)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(1)
                time.sleep(0.001)
            if future.exception():
                raise future.exception()
        self.progressbar.hide()

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class OutputPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(OutputPage, self).__init__(parent)
        self.setTitle("Generating output files")

        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, 0)
        self.progressbar.setAlignment(QtCore.Qt.AlignCenter)
        self.logbox = QtGui.QTextEdit()
        self.log_handler = LogBoxHandler(self.logbox)
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.setFormatter(LogBoxFormatter())
        logging.getLogger().addHandler(self.log_handler)
        self.log_handler.sig.connect(self.logbox.append)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.progressbar)
        layout.addWidget(self.logbox)
        self.setLayout(layout)

    def initializePage(self):
        self.logbox.clear()
        QtCore.QTimer.singleShot(0, self.doGenerateOutput)

    def doGenerateOutput(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.output,
                                     self.wizard().project_path)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(1)
                time.sleep(0.001)
        self.progressbar.hide()

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class FinishPage(QtGui.QWizardPage):
    def __init__(self, config, parent=None):
        super(FinishPage, self).__init__(parent)
        self.setFinalPage(True)
        self.setTitle("Done!")
        # TODO: Offer option to view project folder on exit

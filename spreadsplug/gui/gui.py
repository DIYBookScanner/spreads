import logging
import os
import time

from concurrent.futures import ThreadPoolExecutor
from PySide import QtCore, QtGui
from PIL import Image

import spreads
import spreads.workflow as workflow
from spreads.plugin import get_pluginmanager

import gui_rc

logger = logging.getLogger('spreadsplug.gui')


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
        # Play a warning sound if something has gone wrong
        self.sig.emit(self.format(record))
        if record.levelname in ('ERROR', 'CRITICAL', 'WARNING'):
            QtGui.QApplication.beep()


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
    def __init__(self, config, devices, parent=None):
        super(SpreadsWizard, self).__init__(parent)

        self.devices = devices

        self.addPage(IntroPage())
        self.addPage(CapturePage())
        self.addPage(DownloadPage())
        self.addPage(PostprocessPage())
        self.addPage(OutputPage())
        self.addPage(FinishPage())

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
    def initializePage(self):
        self.pluginmanager = get_pluginmanager()
        self.wizard().active_plugins = self.pluginmanager.names()
        self.setTitle("Welcome!")

        intro_label = QtGui.QLabel(
            "This wizard will guide you through the digitization workflow. "
        )

        dirpick_layout = QtGui.QHBoxLayout()
        self.line_edit = QtGui.QLineEdit()
        browse_btn = QtGui.QPushButton("Browse")
        dirpick_layout.addWidget(self.line_edit)
        dirpick_layout.addWidget(browse_btn)
        browse_btn.clicked.connect(self.show_filepicker)

        form_layout = QtGui.QFormLayout()

        self.keep_box = QtGui.QCheckBox("Keep files on devices")
        form_layout.addRow(self.keep_box)

        # NOTE: Ugly workaround to allow for easier odd/even switch
        # TODO: Find a cleaner way to do this
        self.even_device = None
        if ('combine' in self.wizard().active_plugins
                or 'autorotate' in self.wizard().active_plugins):
            self.even_device = QtGui.QComboBox()
            self.even_device.addItem("Left")
            self.even_device.addItem("Right")
            self.even_device.setCurrentIndex(0)
            form_layout.addRow("Device for even pages", self.even_device)

        # Add configuration widgets from plugins
        self.plugin_widgets = {}
        for ext in self.pluginmanager:
            tmpl = ext.plugin.configuration_template()
            if not tmpl:
                continue
            widgets = self._get_plugin_config_widgets(tmpl)
            self.plugin_widgets[ext.name] = widgets
            for label, widget in widgets.values():
                # We don't need a label for QCheckBoxes
                if isinstance(widget, QtGui.QCheckBox):
                    form_layout.addRow(widget)
                else:
                    form_layout.addRow(label, widget)

        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(intro_label)
        main_layout.addSpacing(30)
        main_layout.addWidget(
            QtGui.QLabel("Please select a project directory.")
        )
        main_layout.addLayout(dirpick_layout)
        main_layout.addSpacing(30)
        main_layout.addLayout(form_layout)

        self.setLayout(main_layout)

    def _get_plugin_config_widgets(self, tmpl):
        widgets = {}
        for key, option in tmpl.items():
            label = (option.docstring
                     if not option.docstring is None else key.title())
            # Do we need a dropdown?
            if (option.selectable and
                    any(isinstance(option.value, x) for x in (list, tuple))):
                widget = QtGui.QComboBox()
                for each in option.value:
                    widget.addItem(each)
                widget.setCurrentIndex(0)
            # Do we need a checkbox?
            elif isinstance(option.value, bool):
                widget = QtGui.QCheckBox(label)
                widget.setCheckState(QtCore.Qt.Checked
                                     if option.value
                                     else QtCore.Qt.Unchecked)
            elif any(isinstance(option.value, x) for x in (list, tuple)):
                # NOTE: We skip options with sequences for a value for now,
                #       as I'm not sure yet how this is best displayed to
                #       the user...
                # TODO: Find a way to display this nicely to the user
                continue
            # Seems like we need another value...
            else:
                widget = QtGui.QLineEdit()
                widget.setText(str(option.value))
                if isinstance(option.value, int):
                    widget.setValidator(QtGui.QIntValidator())
                elif isinstance(option.value, float):
                    widget.setValidator(QtGui.QDoubleValidator())
            widgets[key] = (label, widget)
        return widgets

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

        spreads.config['keep'] = self.keep_box.isChecked()
        if self.even_device and self.even_device.currentText() != 'Left':
            spreads.config['first_page'] = "right"
            spreads.config['rotate_inverse'] = True

        self._update_config_from_plugin_widgets()
        return True

    def _update_config_from_plugin_widgets(self):
        for ext in self.pluginmanager:
            if not ext.name in self.plugin_widgets:
                continue
            logger.debug("Updating config from widgets for plugin {0}"
                         .format(ext.name))
            for key in self.plugin_widgets[ext.name]:
                logger.debug("Trying to set key \"{0}\"".format(key))
                label, widget = self.plugin_widgets[ext.name][key]
                if isinstance(widget, QtGui.QComboBox):
                    idx = widget.currentIndex()
                    values = ext.plugin.configuration_template()[key].value
                    logger.debug("Setting to \"{0}\"".format(values[idx]))
                    spreads.config[ext.name][key] = values[idx]
                elif isinstance(widget, QtGui.QCheckBox):
                    checked = widget.isChecked()
                    logger.debug("Setting to \"{0}\"".format(checked))
                    spreads.config[ext.name][key] = checked
                else:
                    content = spreads.config[ext.name][key] = widget.text()
                    logger.debug("Setting to \"{0}\"".format(content))
                    if isinstance(widget.validator(), QtGui.QIntValidator):
                        spreads.config[ext.name][key] = int(content)
                    elif isinstance(widget.validator(),
                                    QtGui.QDoubleValidator):
                        spreads.config[ext.name][key] = float(content)
                    else:
                        spreads.config[ext.name][key] = unicode(content)


class CapturePage(QtGui.QWizardPage):
    def initializePage(self):
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

        self.refresh_btn = QtGui.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.update_preview)

        self.capture_btn = QtGui.QPushButton("Capture")
        self.capture_btn.clicked.connect(self.doCapture)
        self.capture_btn.setFocus()

        self.logbox = QtGui.QTextEdit()
        self.log_handler = LogBoxHandler(self.logbox)
        self.log_handler.setLevel(logging.WARNING)
        self.log_handler.setFormatter(LogBoxFormatter())
        logging.getLogger().addHandler(self.log_handler)
        self.log_handler.sig.connect(self.logbox.append)

        layout.addWidget(self.status)
        layout.addWidget(self.refresh_btn)
        layout.addLayout(previewbox)
        layout.addWidget(self.capture_btn)
        layout.addWidget(self.logbox)
        self.setLayout(layout)
        time.sleep(0.5)
        self.update_preview()

    def validatePage(self):
        workflow.finish_capture(self.wizard().selected_devices)
        return True

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_B, QtCore.Qt.Key_Space):
            self.doCapture()

    def doCapture(self):
        if self.start_time is None:
            self.start_time = time.time()
        if self.shot_count is None:
            self.shot_count = 0
        self.capture_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.capture,
                                     self.wizard().selected_devices)
            while future.running():
                QtGui.qApp.processEvents()
                time.sleep(0.001)
        self.capture_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.capture_btn.setFocus()
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


class DownloadPage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Downloading")

        #TODO: Display a real progress bar here, update it according to the
        #      combined number of files in raw or its subfolders
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
        self.logbox.clear()
        QtCore.QTimer.singleShot(0, self.doDownload)

    def doDownload(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.download,
                                     self.wizard().selected_devices,
                                     self.wizard().project_path)
            while future.running():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(0)
                time.sleep(0.001)
            if future.exception():
                raise future.exception()
        self.progressbar.hide()
        if ('combine' in self.wizard().active_plugins and not
                os.listdir(os.path.join(self.wizard().project_path, 'raw'))):
            msg_box = QtGui.QMessageBox()
            msg_box.setText("It seems that combining the images has failed."
                            "Please fix the issue manually and retry.")
            # TODO: Add a 'combine' button to retry combining.
            msg_box.setIcon(QtGui.QMessageBox.Critical)
            self.combine_btn = msg_box.addButton("Combine",
                                                 QtGui.QMessageBox.ApplyRole)
            self.combine_btn.clicked.connect(get_pluginmanager()['combine']
                                             .download(self.wizard()
                                             .project_path))
            msg_box.exec_()

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class PostprocessPage(QtGui.QWizardPage):
    def initializePage(self):
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
        self.logbox.clear()
        QtCore.QTimer.singleShot(0, self.doPostprocess)

    def doPostprocess(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.process,
                                     self.wizard().project_path)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(0)
                time.sleep(0.01)
            if future.exception():
                raise future.exception()
        self.progressbar.hide()

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class OutputPage(QtGui.QWizardPage):
    def initializePage(self):
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
        self.logbox.clear()
        QtCore.QTimer.singleShot(0, self.doGenerateOutput)

    def doGenerateOutput(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.output,
                                     self.wizard().project_path)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(0)
                time.sleep(0.001)
        self.progressbar.hide()

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class FinishPage(QtGui.QWizardPage):
    def initializePage(self):
        self.setFinalPage(True)
        self.setTitle("Done!")
        # TODO: Offer option to view project folder on exit

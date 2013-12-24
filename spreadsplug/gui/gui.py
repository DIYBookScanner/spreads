import logging
import time

from concurrent.futures import ThreadPoolExecutor
from PySide import QtCore, QtGui

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
        try:
            self.sig.emit(self.format(record))
        except:
            self.handleError(record)

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
        return self.LEVELS[levelname].format(record.msg)


class SpreadsWizard(QtGui.QWizard):
    def __init__(self, config, parent=None):
        super(SpreadsWizard, self).__init__(parent)

        self.config = config

        self.addPage(IntroPage())
        self.addPage(CapturePage())
        self.addPage(PostprocessPage())
        self.addPage(OutputPage())

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
        self.setFixedWidth(700)


class IntroPage(QtGui.QWizardPage):
    def initializePage(self):
        wizard = self.wizard()
        self.pluginmanager = get_pluginmanager(wizard.config)
        wizard.active_plugins = self.pluginmanager.names()
        self.setTitle("Welcome!")

        intro_label = QtGui.QLabel(
            "This wizard will guide you through the digitization workflow. "
        )
        intro_label.setWordWrap(True)

        dirpick_layout = QtGui.QHBoxLayout()
        self.line_edit = QtGui.QLineEdit()
        self.line_edit.textChanged.connect(self.completeChanged)
        browse_btn = QtGui.QPushButton("Browse")
        dirpick_layout.addWidget(self.line_edit)
        dirpick_layout.addWidget(browse_btn)
        browse_btn.clicked.connect(self.show_filepicker)

        self.stack_widget = QtGui.QStackedWidget()
        page_combobox = QtGui.QComboBox()
        page_combobox.activated.connect(self.stack_widget.setCurrentIndex)
        #QtCore.QObject.connect(page_combobox, SIGNAL("activated(int)"),
        #        self.stack_widget, SLOT("setCurrentIndex(int)"))

        # Add configuration widgets from plugins
        self.plugin_widgets = {}
        for ext in self.pluginmanager:
            tmpl = ext.plugin.configuration_template()
            if not tmpl:
                continue
            page = QtGui.QGroupBox()
            layout = QtGui.QFormLayout()
            widgets = self._get_plugin_config_widgets(tmpl)
            self.plugin_widgets[ext.name] = widgets
            for label, widget in widgets.values():
                # We don't need a label for QCheckBoxes
                if isinstance(widget, QtGui.QCheckBox):
                    layout.addRow(widget)
                else:
                    layout.addRow(label, widget)
            page.setLayout(layout)
            self.stack_widget.addWidget(page)
            page_combobox.addItem(ext.name.title())

        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(intro_label)
        main_layout.addSpacing(30)
        main_layout.addWidget(
            QtGui.QLabel("Please select a project directory.")
        )
        main_layout.addLayout(dirpick_layout)
        main_layout.addSpacing(30)
        main_layout.addWidget(page_combobox)
        main_layout.addWidget(self.stack_widget)
        main_layout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)

        self.setLayout(main_layout)
        self.adjustSize()

    def _get_plugin_config_widgets(self, plugin_tmpl):
        widgets = {}
        for key, option in plugin_tmpl.items():
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
            elif isinstance(option.value, int):
                widget = QtGui.QSpinBox()
                widget.setMaximum(1024)
                widget.setMinimum(-1024)
                widget.setValue(option.value)
            elif isinstance(option.value, float):
                widget = QtGui.QDoubleSpinBox()
                widget.setMaximum(1024.0)
                widget.setMinimum(-1024.0)
                widget.setValue(option.value)
            else:
                widget = QtGui.QLineEdit()
                widget.setText(option.value)
            widgets[key] = (label, widget)
        return widgets

    def show_filepicker(self):
        dialog = QtGui.QFileDialog()
        dialog.setFileMode(QtGui.QFileDialog.Directory)
        dialog.setOption(QtGui.QFileDialog.ShowDirsOnly, True)
        dialog.exec_()
        self.line_edit.setText(dialog.selectedFiles()[0])

    def isComplete(self):
        return bool(self.line_edit.text())

    def validatePage(self):
        wizard = self.wizard()
        project_path = self.line_edit.text()
        if not project_path:
            msg_box = QtGui.QMessageBox()
            msg_box.setText("Please select a project directory.")
            msg_box.setIcon(QtGui.QMessageBox.Critical)
            msg_box.exec_()
            return False

        self._update_config_from_plugin_widgets()
        wizard.workflow = workflow.Workflow(path=project_path,
                                            config=wizard.config)
        wizard.workflow.prepare_capture()
        return True

    def _update_config_from_plugin_widgets(self):
        config = self.wizard().config
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
                    config[ext.name][key] = values[idx]
                elif isinstance(widget, QtGui.QCheckBox):
                    checked = widget.isChecked()
                    logger.debug("Setting to \"{0}\"".format(checked))
                    config[ext.name][key] = checked
                elif any(isinstance(widget, x)
                         for x in (QtGui.QSpinBox, QtGui.QDoubleSpinBox)):
                    config[ext.name][key] = widget.value()
                else:
                    content = config[ext.name][key] = widget.text()
                    logger.debug("Setting to \"{0}\"".format(content))
                    config[ext.name][key] = unicode(content)


class CapturePage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Capturing from devices")
        self.start_time = None
        self.shot_count = None

        # TODO: Add horizontally scrolling box with thumbnails of all
        #       previously shot images
        # TODO: Display last two shot images next to each other
        # TODO: Add button to retake the last capture

        layout = QtGui.QVBoxLayout(self)
        self.status = QtGui.QLabel("Press a capture key (default: Space, B)"
                                   " to begin capturing.")

        self.capture_btn = QtGui.QPushButton("Capture")
        self.capture_btn.clicked.connect(self.doCapture)
        self.capture_btn.setFocus()

        control_layout = QtGui.QHBoxLayout()
        self.control_odd = QtGui.QLabel()
        self.control_even = QtGui.QLabel()
        control_layout.addWidget(self.control_odd)
        control_layout.addWidget(self.control_even)

        self.retake_btn = QtGui.QPushButton("Retake")
        self.retake_btn.clicked.connect(self.retakeCapture)
        self.retake_btn = QtGui.QPushButton("Retake")
        self.retake_btn.clicked.connect(self.retakeCapture)

        self.logbox = QtGui.QTextEdit()
        self.log_handler = LogBoxHandler(self.logbox)
        self.log_handler.setLevel(logging.WARNING)
        self.log_handler.setFormatter(LogBoxFormatter())
        logging.getLogger().addHandler(self.log_handler)
        self.log_handler.sig.connect(self.logbox.append)

        layout.addWidget(self.status)
        layout.addStretch(1)
        layout.addLayout(control_layout)
        layout.addWidget(self.capture_btn)
        layout.addWidget(self.retake_btn)
        layout.addWidget(self.logbox)
        self.setLayout(layout)

    def validatePage(self):
        self.wizard().workflow.finish_capture()
        return True

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_B, QtCore.Qt.Key_Space):
            self.doCapture()

    def updateControl(self):
        images = self.wizard().workflow.images
        self.control_odd.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(unicode(images[-2]))
                                    .scaledToWidth(250)))
        self.control_even.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(unicode(images[-1]))
                                    .scaledToWidth(250)))

    def retakeCapture(self):
        self.retake_btn.setEnabled(False)
        self.doCapture(retake=True)
        self.retake_btn.setEnabled(True)

    def doCapture(self, retake=False):
        self.capture_btn.setEnabled(False)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.wizard().workflow.capture, retake)
            while future.running():
                QtGui.qApp.processEvents()
                time.sleep(0.001)
        self.capture_btn.setEnabled(True)
        self.capture_btn.setFocus()
        pages_shot = self.wizard().workflow._pages_shot
        start_time = self.wizard().workflow.capture_start
        self.status.setText(
            "Shot {0} pages in {1:.0f} minutes ({2:.0f} pages/hour)"
            .format(pages_shot, (time.time() - start_time) / 60,
                    ((3600 / (time.time() - start_time)) * pages_shot)))
        self.updateControl()


class PostprocessPage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Postprocessing")

        self.done = False

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
            future = executor.submit(self.wizard().workflow.process)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(0)
                time.sleep(0.01)
            if future.exception():
                raise future.exception()
        self.progressbar.hide()
        self.done = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.done

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True


class OutputPage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Generating output files")
        self.setFinalPage(True)

        self.done = False

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
            future = executor.submit(self.wizard().workflow.output)
            while not future.done():
                QtGui.qApp.processEvents()
                self.progressbar.setValue(0)
                time.sleep(0.001)
        self.progressbar.hide()
        self.done = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.done

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True

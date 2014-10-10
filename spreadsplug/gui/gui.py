# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import time

from concurrent.futures import ThreadPoolExecutor
from PySide import QtCore, QtGui

import spreads.plugin as plugin
import spreads.workflow as workflow

import gui_rc  # noqa

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
            QtGui.QApplication.instance().beep()


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

        button_layout = [
            QtGui.QWizard.BackButton, QtGui.QWizard.Stretch,
            QtGui.QWizard.CancelButton, QtGui.QWizard.Stretch,
            QtGui.QWizard.NextButton, QtGui.QWizard.FinishButton
        ]
        self.setButtonLayout(button_layout)

        self.setWindowTitle("Spreads Wizard")
        self.setFixedWidth(700)


class IntroPage(QtGui.QWizardPage):
    def initializePage(self):
        wizard = self.wizard()
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
        self.tab_widget = QtGui.QTabWidget()

        # Add configuration widgets from plugins
        self.plugin_widgets = {}

        # Filter out subcommand plugins
        available = [
            name for name, cls
            in plugin.get_plugins(*wizard.config['plugins'].get()).items()
            if not issubclass(cls, plugin.SubcommandHooksMixin)
        ]
        available.append('device')

        for name, tmpl in wizard.config.templates.iteritems():
            if not tmpl or name not in available:
                continue
            page = QtGui.QGroupBox()
            layout = QtGui.QFormLayout()
            widgets = self._get_plugin_config_widgets(tmpl, name)
            self.plugin_widgets[name] = widgets
            for label, widget in widgets.values():
                # We don't need a label for QCheckBoxes
                if isinstance(widget, QtGui.QCheckBox):
                    layout.addRow(widget)
                else:
                    layout.addRow(label, widget)
            page.setLayout(layout)
            self.tab_widget.addTab(page, name.title())

        self.save_btn = QtGui.QPushButton("&Save as defaults")
        self.save_btn.clicked.connect(self.saveSettings)
        save_layout = QtGui.QHBoxLayout()
        save_layout.addStretch(1)
        save_layout.addWidget(self.save_btn)

        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(intro_label)
        main_layout.addSpacing(30)
        main_layout.addWidget(
            QtGui.QLabel("Please select a project directory.")
        )
        main_layout.addLayout(dirpick_layout)
        main_layout.addSpacing(30)
        main_layout.addWidget(self.tab_widget)
        main_layout.addLayout(save_layout)
        main_layout.setSizeConstraint(QtGui.QLayout.SetNoConstraint)

        self.setLayout(main_layout)
        self.adjustSize()

    def _get_plugin_config_widgets(self, plugin_tmpl, plugname):
        # TODO: Find solution for the `depends` option, i.e. making the display
        # of a widget dependent on the value of some other setting
        widgets, config = {}, self.wizard().config
        for key, option in plugin_tmpl.items():
            label = (option.docstring
                     if option.docstring is not None else key.title())
            cur_value = config[plugname][key].get()
            # Do we need a dropdown?
            if (option.selectable and
                    any(isinstance(option.value, x) for x in (list, tuple))):
                widget = QtGui.QComboBox()
                i, index = 0, 0
                for each in option.value:
                    widget.addItem(unicode(each))
                    if each == cur_value:
                        index = i
                    i += 1
                widget.setCurrentIndex(index)
            # Do we need a checkbox?
            elif isinstance(option.value, bool):
                widget = QtGui.QCheckBox(label)
                widget.setCheckState(QtCore.Qt.Checked
                                     if cur_value
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
                maxVlu = max(1024, option.value * 2)
                widget.setMaximum(maxVlu)
                widget.setMinimum(-maxVlu)
                widget.setValue(cur_value)
            elif isinstance(option.value, float):
                widget = QtGui.QDoubleSpinBox()
                maxVlu = max(1024.0, option.value * 2)
                widget.setMaximum(maxVlu)
                widget.setMinimum(-maxVlu)
                widget.setValue(cur_value)
            else:
                widget = QtGui.QLineEdit()
                widget.setText(cur_value)
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

    def saveSettings(self):
        self._update_config_from_plugin_widgets()
        config = self.wizard().config
        logger.debug("Writing configuration file to '{0}'"
                     .format(config.cfg_path))
        config.dump(filename=config.cfg_path)

    def _update_config_from_plugin_widgets(self):
        config = self.wizard().config
        for section in config.templates:
            if section not in self.plugin_widgets:
                continue
            logger.debug("Updating config from widgets for plugin {0}"
                         .format(section))
            for key in self.plugin_widgets[section]:
                logger.debug("Trying to set key \"{0}\"".format(key))
                label, widget = self.plugin_widgets[section][key]
                if isinstance(widget, QtGui.QComboBox):
                    idx = widget.currentIndex()
                    values = config.templates[section][key].value
                    logger.debug("Setting to \"{0}\"".format(values[idx]))
                    config[section][key] = values[idx]
                elif isinstance(widget, QtGui.QCheckBox):
                    checked = widget.isChecked()
                    logger.debug("Setting to \"{0}\"".format(checked))
                    config[section][key] = checked
                elif any(isinstance(widget, x)
                         for x in (QtGui.QSpinBox, QtGui.QDoubleSpinBox)):
                    config[section][key] = widget.value()
                else:
                    content = config[section][key] = widget.text()
                    logger.debug("Setting to \"{0}\"".format(content))
                    config[section][key] = unicode(content)


class CapturePage(QtGui.QWizardPage):
    def initializePage(self):
        self.setTitle("Capturing from devices")
        self.start_time = None
        self.shot_count = 0

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
        images = [p.raw_image for p in self.wizard().workflow.pages[-2:]]
        self.control_odd.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(unicode(images[0]))
                                    .scaledToWidth(250)))
        self.control_even.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(unicode(images[1]))
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
        self.shot_count += len(self.wizard().workflow.devices)
        if hasattr(self, '_start_time'):
            capture_speed = ((3600 / (time.time() - self._start_time))
                             * self.shot_count)
        else:
            self._start_time = time.time()
            capture_speed = 0.0
        self.status.setText(
            "Shot {0} pages in {1:.0f} minutes ({2:.0f} pages/hour)"
            .format(self.shot_count, (time.time() - self._start_time) / 60,
                    capture_speed))
        self.updateControl()


class PostprocessPage(QtGui.QWizardPage):
    done = False
    progress = QtCore.Signal(int)

    def initializePage(self):
        self.setTitle("Postprocessing")

        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, 100)
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
        # Workaround for Qt threading issue:
        # QWidget::repaint: Recursive repaint detected, Segfaults
        # Use Qt event loop instead, it's thread safe
        def progress_callback(wf, changes):
            if 'status' in changes and 'step_progress' in changes['status']:
                self.progress.emit(
                    int(changes['status']['step_progress']*100))

        QtCore.QObject.connect(self, QtCore.SIGNAL("progress(int)"),
                               self.progressbar, QtCore.SLOT("setValue(int)"))

        workflow.on_modified.connect(progress_callback, weak=False,
                                     sender=self.wizard().workflow)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.wizard().workflow.process)
            while not future.done():
                QtGui.qApp.processEvents()
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
    done = False
    progress = QtCore.Signal(int)

    def initializePage(self):
        self.setTitle("Generating output files")
        self.setFinalPage(True)

        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, 100)
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
        # Workaround for Qt threading issue:
        # QWidget::repaint: Recursive repaint detected, Segfaults
        # Use Qt event loop instead, it's thread safe
        def progress_callback(wf, changes):
            if 'status' in changes and 'step_progress' in changes['status']:
                self.progress.emit(
                    int(changes['status']['step_progress']*100))

        QtCore.QObject.connect(self, QtCore.SIGNAL("progress(int)"),
                               self.progressbar, QtCore.SLOT("setValue(int)"))

        workflow.on_modified.connect(progress_callback, weak=False,
                                     sender=self.wizard().workflow)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.wizard().workflow.output)
            while not future.done():
                QtGui.qApp.processEvents()
                time.sleep(0.01)
        self.progressbar.hide()
        self.done = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.done

    def validatePage(self):
        logging.getLogger().removeHandler(self.log_handler)
        return True

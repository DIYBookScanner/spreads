import logging

from PySide import QtGui

import spreads
from spreads.plugin import HookPlugin, get_devices
import gui
import gui_rc

logger = logging.getLogger('spreadsplug.gui')


class GuiCommand(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        guiparser = rootparser.add_parser(
            'gui', help="Start the GUI wizard")
        guiparser.set_defaults(subcommand=GuiCommand.wizard)

    @staticmethod
    def wizard(config):
        logger.debug("Starting GUI")
        app = QtGui.QApplication([])
        # NOTE: This is a bit hackish....
        #       Since the GUI creates its own workflow object(s), we here only
        #       pass the configuration and the devices from the CLI workflow
        wizard = gui.SpreadsWizard(config)
        wizard.show()
        app.exec_()

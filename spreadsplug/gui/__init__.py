import logging

from PySide import QtGui

from spreads.plugin import HookPlugin, SubcommandHookMixin
import gui
import gui_rc

logger = logging.getLogger('spreadsplug.gui')


class GuiCommand(HookPlugin, SubcommandHookMixin):
    @classmethod
    def add_command_parser(cls, rootparser):
        guiparser = rootparser.add_parser(
            'gui', help="Start the GUI wizard")
        guiparser.set_defaults(subcommand=GuiCommand.wizard)

    @staticmethod
    def wizard(config):
        logger.debug("Starting GUI")
        app = QtGui.QApplication([])

        wizard = gui.SpreadsWizard(config)
        wizard.show()
        app.exec_()

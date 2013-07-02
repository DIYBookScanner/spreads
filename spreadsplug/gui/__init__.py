from PySide import QtGui

import spreads
from spreads.plugin import HookPlugin
import gui
import gui_rc


class GuiCommand(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        guiparser = rootparser.add_parser(
            'gui', help="Start the GUI wizard")
        guiparser.set_defaults(func=wizard)


def wizard(args):
    app = QtGui.QApplication([])
    wizard = gui.SpreadsWizard(spreads.config)
    wizard.show()
    app.exec_()

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

"""
Graphical configuration dialog.
"""

from __future__ import division, unicode_literals

import logging
import Tkinter as tk
import tkMessageBox as messagebox
import ttk

import spreads.plugin as plugin

logger = logging.getLogger("guiconfig")

# TODO: Implement inter-dependant display of widgets


class TkConfigurationWindow(tk.Frame):
    """ Window that holds the dialog """
    def __init__(self, spreads_config, master=None):
        """ Initialize Window with global configuration.

        :param spreads_config:  Global configuration
        :type spreads_config:   :py:class:`spreads.config.Configuration`
        """
        tk.Frame.__init__(self, master)
        self.spreads_config = spreads_config
        self.grid()
        self.create_plugin_widgets()
        self.create_driver_widgets()

        self.save_btn = ttk.Button(self, text="Save", command=self.save_config)
        self.save_btn.grid(column=0, row=7, columnspan=2)

        self.load_values()

    def update_plugin_config(self, plugins):
        """ Update list of activated plugins and load its default
            configuration.

        :param plugins:     List of names of plugins to activate
        :type plugins:      list of unicode
        """
        config = self.spreads_config
        new_plugins = [x for x in plugins
                       if x not in config["plugins"].get()]
        config["plugins"] = plugins
        for name in new_plugins:
            if name not in config.templates:
                logger.debug("No template found for {0}".format(name))
                continue
            self.spreads_config.set_from_template(name, config.templates[name])

    def on_update_driver(self, event):
        """ Callback for when the user selects a driver.

        Updates the driver in the configuration and toggles the status of
        widgets that depend on certain device features.

        :param event:   Event from Tkinter
        :type event:    :py:class:`Tkinter.Event`
        """
        driver_name = self.driver_select.get()
        driver = plugin.get_driver(driver_name)
        self.spreads_config["driver"] = driver_name
        if plugin.DeviceFeatures.IS_CAMERA in driver.features:
            for widget in (self.orient_label, self.orient_odd_btn,
                           self.orient_even_btn, self.focus_label,
                           self.focus_btn):
                widget['state'] = "enabled"

    def on_update_plugin_selection(self, event):
        """ Callback for when the user toggles a plugin.

        Tries to load the newly selected plugins. If loading fails, a dialog
        with the cause of failure will be displayed and the plugin will be
        highlighted in the list and made inactive. If successful, the plugin
        will be added to the 'postprocessing order' widget (if it implements
        :py:class:`spreads.plugin.ProcessHooksMixin`) and the configuration
        will be updated.

        :param event:   Event from Tkinter
        :type event:    :py:class:`Tkinter.Event`
        """
        selection = self.plugin_select.selection()
        self.selected_plugins = list(selection)
        try:
            exts = [name for name, cls in plugin.get_plugins(*selection)
                    .iteritems() if issubclass(cls, plugin.ProcessHooksMixin)]
        except plugin.ExtensionException as e:
            exts = []
            failed_ext = e.extension
            messagebox.showerror(message=e.message)
            ext_id = self.plugin_select.index(failed_ext)
            self.plugin_select.delete(failed_ext)
            self.plugin_select.insert('', ext_id, failed_ext, text=failed_ext,
                                      tags=["missingdep"])

            selection = tuple(x for x in selection if x != failed_ext)
        for item in selection:
            if item in exts:
                if not self.processorder_tree.exists(item):
                    self.processorder_tree.insert('', 'end', item, text=item)
            else:
                continue
        for item in self.processorder_tree.get_children():
            if item not in selection:
                self.processorder_tree.delete(item)
        self.update_plugin_config(selection)

    def on_process_plugin_move(self, event):
        """ Callback for when the user changes the position of a plugin in
            the postprocessing order widget.

        Updates the widget and writes the new order to the configuration.

        :param event:   Event from Tkinter
        :type event:    :py:class:`Tkinter.Event`
        """
        tree = event.widget
        moveto = tree.index(tree.identify_row(event.y))
        tree.move(tree.selection()[0], '', moveto)
        self.update_plugin_config(
            [x for x in self.spreads_config["plugins"].get()
             if x not in tree.get_children()] + list(tree.get_children()))

    def create_driver_widgets(self):
        """ Create widgets for driver-related actions. """
        # Dropdown for driver selection
        self.driver_label = ttk.Label(self, text="Select a driver")
        self.driver_label.grid(column=0, row=2, sticky="E")
        self.driver_select = ttk.Combobox(
            self, values=plugin.available_drivers(), state="readonly")
        self.driver_select.bind("<<ComboboxSelected>>", self.on_update_driver)
        self.driver_select.grid(column=1, row=2, sticky="WE")

        # Buttons for setting of target page
        self.orient_label = ttk.Label(self, text="Set device for target pages",
                                      state="disabled")
        self.orient_label.grid(column=0, row=3, columnspan=2)
        self.orient_odd_btn = ttk.Button(
            self, text="Odd pages", state="disabled",
            command=lambda: self.set_orientation('odd'))
        self.orient_odd_btn.grid(column=0, row=4)
        self.orient_even_btn = ttk.Button(
            self, text="Even pages", state="disabled",
            command=lambda: self.set_orientation('even'))
        self.orient_even_btn.grid(column=1, row=4)

        # Button to configure device focus
        self.focus_label = ttk.Label(self, text="Configure focus",
                                     state="disabled")
        self.focus_label.grid(column=0, row=5, columnspan=2)
        self.focus_btn = ttk.Button(self, text="Start", state="disabled",
                                    command=self.configure_focus)
        self.focus_btn.grid(column=0, row=6, columnspan=2)

    def create_plugin_widgets(self):
        """ Create widgets for plugin-related actions. """
        available_plugins = plugin.available_plugins()

        # List of available boxes with checkboxes
        self.plugin_label = ttk.Label(self, text="Select plugins\n"
                                                 "to be activated")
        self.plugin_label.grid(column=0, row=0, sticky="E")
        self.plugin_select = ttk.Treeview(self, height=len(available_plugins),
                                          show=["tree"])
        self.plugin_select.tag_configure('missingdep', foreground="red")
        for plug in available_plugins:
            self.plugin_select.insert('', 'end', plug, text=plug)
        self.plugin_select.bind(
            "<<TreeviewSelect>>", self.on_update_plugin_selection
        )
        self.plugin_select.grid(column=1, row=0, sticky="WE")

        # Widget to configure postprocessing plugin order
        self.processorder_label = ttk.Label(
            self, text="Select order of\npostprocessing plugins")
        self.processorder_label.grid(column=0, row=1, sticky="E")
        self.processorder_tree = ttk.Treeview(
            self, height=5, show=["tree"],
            selectmode="browse")
        self.processorder_tree.bind("<B1-Motion>", self.on_process_plugin_move,
                                    add='+')
        self.processorder_tree.grid(column=1, row=1)

    def load_values(self):
        """ Set widget state from configuration. """
        if 'driver' in self.spreads_config.keys():
            self.driver_select.set(self.spreads_config["driver"].get())
            self.on_update_driver(None)
        for plugname in self.spreads_config["plugins"].get():
            self.plugin_select.selection_add(plugname)
            # NOTE: Force update so the order is kept
            self.on_update_plugin_selection(None)

    def set_orientation(self, target):
        """ Set target page on a device.

        Prompts the user to connect a device, prompts to retry or cancel
        on failure. If successful, updates the target page setting on the
        device.

        :param target:  Target page to set on device
        :type target:   unicode, one of "odd" or "even"
        """
        rv = messagebox.askokcancel(
            message=("Please connect and turn on the camera for {0} pages"
                     .format(target)),
            title="Configure target page")
        if not rv:
            return
        devs = []
        while True:
            try:
                devs = plugin.get_devices(self.spreads_config,
                                          force_reload=True)
            except plugin.DeviceException:
                devs = []
            if not devs:
                errmsg = "No devices could be found."
            elif len(devs) > 1:
                errmsg = "Make sure only one device is turned on!"
            else:
                break
            rv = messagebox.askretrycancel(message=errmsg, title="Error")
            if not rv:
                return

        devs[0].set_target_page(target)
        messagebox.showinfo(message="Please turn off the device.")

    def configure_focus(self):
        """ Acquire auto-focus value from devices and update the configuration
            with it.

        Prompts the user to connect a device, asks for cancel/retry on failure.
        On successful connection, acquires focus and writes the value to the
        configuration.
        """
        # TODO: Handle independent focus for both devices
        rv = messagebox.askokcancel(
            message="Please connect and turn on one of your cameras.",
            title="Configure focus")
        if not rv:
            return
        while True:
            try:
                devs = plugin.get_devices(self.spreads_config,
                                          force_reload=True)
                focus = devs[0]._acquire_focus()
                self.spreads_config['device']['focus_distance'] = focus
                break
            except plugin.DeviceException:
                rv = messagebox.askretrycancel(
                    message="No devices could be found."
                )
                if not rv:
                    break
                else:
                    continue

    def save_config(self):
        """ Write configuration to disk. """
        config = self.spreads_config
        config.dump(filename=config.cfg_path)


def configure(config):
    """ Initialize and display configuration dialog. """
    app = TkConfigurationWindow(config)
    app.master.title = "Initial configuration"
    app.master.resizable(False, False)
    tk.mainloop()

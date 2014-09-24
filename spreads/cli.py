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
Command-Line interface for configuration, capture, output and postprocessing.
"""

from __future__ import division, unicode_literals, print_function

import sys
import time

import colorama

import spreads.workflow
import spreads.plugin as plugin
from spreads.util import DeviceException, colorize

if sys.platform == 'win32':
    # On Windows, getch is included in the standard library
    import msvcrt
    getch = msvcrt.getch()
else:
    # On POSIX systems we have to do it ourselves
    import termios
    import tty

    def getch():
        """ Waits for a single character to be entered on stdin and returns it.

        :return:    Character that was entered
        :rtype:     str
        """
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        char = None
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return char


def draw_progress(progress):
    """ Draw a progress bar to stdout.

    :param progress:    Progress value between 0 and 1
    :type progress:     float
    """
    width = 32
    num_bars = int(width*progress/1.0)
    sys.stdout.write('[{0}{1}] {2}%\r'.format(
        '#'*num_bars,
        ' '*(width-num_bars), int(progress*100)))
    sys.stdout.flush()


def _select_driver(current):
    """ Display driver selection dialog.

    :param current:     Name of currently selected driver
    :return:            Name of newly selected driver
    """
    print(colorize("Please select a device driver from the following list:",
                   colorama.Fore.BLUE))
    # Add None as an option to configure spreads without a device
    available_drivers = plugin.available_drivers() + [None]
    print("  [0]: Keep current ({0})".format(current))
    for pos, ext in enumerate(available_drivers, 1):
        print("  [{0}]: {1}".format(pos, ext))
    while True:
        selection = raw_input("Select a driver: ")
        if not selection or int(selection) == 0:
            return current
        if not selection.isdigit() or int(selection) > len(available_drivers):
            print(colorize("Please select a number in the range of 0 to {0}"
                           .format(len(available_drivers)), colorama.Fore.RED))
            continue
        driver = unicode(available_drivers[int(selection)-1])
        print(colorize("Selected \"{0}\" as device driver".format(driver),
                       colorama.Fore.GREEN))
        return driver


def _select_plugins(preselected=None):
    """ Display plugin selection dialog.

    :param preselected:     Names of currently selected plugins
    :return:                Names of newly selected plugins
    """
    if preselected is None:
        selected_plugins = []
    else:
        # Create a local clone of the preselected list
        selected_plugins = preselected[:]
    print("Please select your desired plugins from the following list:")
    available_plugins = plugin.available_plugins()
    while True:
        for pos, ext in enumerate(available_plugins, 1):
            print("  {0} {1}: {2}"
                  .format('x' if ext in selected_plugins else ' ', pos, ext))
        selection = raw_input("Select a plugin (or hit enter to finish): ")
        if not selection:
            break
        if not selection.isdigit() or int(selection) > len(available_plugins):
            print(colorize("Please select a number in the range of 1 to {0}"
                           .format(len(available_plugins)), colorama.Fore.RED))
            continue
        plugin_name = available_plugins[int(selection)-1]
        if plugin_name in selected_plugins:
            selected_plugins.remove(plugin_name)
        else:
            selected_plugins.append(plugin_name)
    return selected_plugins


def _setup_processing_pipeline(config):
    """ Display dialog to configure order of postprocessing plugins and update
    the configuration accordingly.

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    # Only get names of postprocessing plugins. For this we have to load all
    # enabled plugins first and check if they implement the correct hook.
    exts = [name for name, cls in plugin.get_plugins(*config["plugins"].get())
            .iteritems() if issubclass(cls, plugin.ProcessHookMixin)]
    if not exts:
        return
    print("The following postprocessing plugins were detected:")
    print("\n".join(" - {0}".format(ext) for ext in exts))
    while True:
        answer = raw_input("Please enter the extensions in the order that they"
                           " should be invoked, separated by commas or hit"
                           " enter to keep the current order:\n")
        if not answer:
            plugins = exts
        else:
            plugins = [x.strip() for x in answer.split(',')]
        if any(x not in exts for x in plugins):
            print(colorize("At least one of the entered extensions was not"
                           "found, please try again!", colorama.Fore.RED))
        else:
            break
    # Append other plugins after the postprocessing plugins
    config["plugins"] = plugins + [x for x in config["plugins"].get()
                                   if x not in plugins]


def _set_device_target_page(config, target_page):
    """ Display dialog for setting the target page on a device.

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    :param target_page: Target page to set on the device
    :type target_page:  One of 'odd' or 'even'
    """
    print("Please connect and turn on the device labeled \'{0}\'"
          .format(target_page))
    print("Press any key when ready.")
    getch()
    devs = plugin.get_devices(config, force_reload=True)
    if len(devs) > 1:
        raise DeviceException("Please ensure that only one device is"
                              " turned on!")
    if not devs:
        raise DeviceException("No device found!")
    devs[0].set_target_page(target_page)
    print(colorize("Configured \'{0}\' device.".format(target_page),
                   colorama.Fore.GREEN))
    print("Please turn off the device.")
    print("Press any key when ready.")
    getch()


def configure(config):
    """ Configuration subcommand that runs through the various dialogs, builds
    a new configuration and writes it to disk.

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    old_plugins = config["plugins"].get()
    driver_name = _select_driver(
        config["driver"].get() if 'driver' in config.keys() else None)
    if driver_name:
        config["driver"] = driver_name
        driver = plugin.get_driver(config["driver"].get())
    else:
        driver = None
    # Save driver
    config.dump(filename=config.cfg_path)

    config["plugins"] = _select_plugins(old_plugins)
    _setup_processing_pipeline(config)

    # Load default configuration for newly added plugins
    new_plugins = [x for x in config["plugins"].get() if x not in old_plugins]
    for name in new_plugins:
        if not name in config.templates:
            continue
        config.set_from_template(name, config.templates[name])

    # Save plugins
    config.dump(filename=config.cfg_path)

    # We only need to set the device target_page if the driver supports
    # shooting with two devices
    if driver and plugin.DeviceFeatures.IS_CAMERA in driver.features:
        answer = raw_input(
            "Do you want to configure the target_page of your devices?\n"
            "(Required for shooting with two devices) [y/N]: ")
        answer = True if answer.lower() == 'y' else False
        if answer:
            print("Setting target page on cameras")
            for target_page in ('odd', 'even'):
                _set_device_target_page(config, target_page)

        answer = raw_input("Do you want to setup the focus for your cameras? "
                           "[y/N]: ")
        answer = True if answer.lower() == 'y' else False
        if answer:
            # TODO: Set focus for both devices independently
            print("Please turn on one of your capture devices.\n"
                  "Press any key to continue")
            getch()
            devs = plugin.get_devices(config, force_reload=True)
            print("Please put a book with as little whitespace as possible"
                  "under your cameras.\nPress any button to continue")
            getch()
            focus = devs[0]._acquire_focus()
            config['device']['focus_mode'] = 'manual'
            config['device']['focus_distance'] = focus
        else:
            config['device']['focus_mode'] = 'autofocus_all'
    print("Configuration file written to '{0}'".format(config.cfg_path))
    config.dump(filename=config.cfg_path)


def capture(config):
    """ Dialog to run through the capture process.

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    path = config['path'].get()
    workflow = spreads.workflow.Workflow(config=config, path=path)
    spreads.workflow.on_created.send(workflow)
    capture_keys = workflow.config['core']['capture_keys'].as_str_seq()

    # Some closures
    def _refresh_stats():
        """ Callback that prints up-to-date capture statistics to stdout """
        if _refresh_stats.start_time is not None:
            pages_per_hour = ((3600/(time.time() - _refresh_stats.start_time))
                              * len(workflow.pages))
        else:
            pages_per_hour = 0.0
            _refresh_stats.start_time = time.time()
        status = ("\rShot {0: >3} pages [{1: >4.0f}/h] "
                  .format(len(workflow.pages), pages_per_hour))
        sys.stdout.write(status)
        sys.stdout.flush()
    _refresh_stats.start_time = None

    def _trigger_loop():
        """ Waits for input on stdin and launches appropriate actions. """
        is_posix = sys.platform != 'win32'
        old_count = len(workflow.pages)
        if is_posix:
            import select
            old_settings = termios.tcgetattr(sys.stdin)
            data_available = lambda: (select.select([sys.stdin], [], [], 0) ==
                                      ([sys.stdin], [], []))
            read_char = lambda: sys.stdin.read(1)
        else:
            data_available = msvcrt.kbhit
            read_char = msvcrt.getch

        try:
            if is_posix:
                tty.setcbreak(sys.stdin.fileno())
            while True:
                time.sleep(0.01)
                if len(workflow.pages) != old_count:
                    old_count = len(workflow.pages)
                    _refresh_stats()
                if not data_available():
                    continue
                char = read_char()
                if char in tuple(capture_keys) + ('r', ):
                    # Capture or retake
                    workflow.capture(retake=(char == 'r'))
                    _refresh_stats()
                elif char == 'f':
                    # Finish capturing
                    break
        finally:
            if is_posix:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    if len(workflow.devices) != 2:
        raise DeviceException("Please connect and turn on two"
                              " pre-configured devices! ({0} were"
                              " found)".format(len(workflow.devices)))
    print(colorize("Found {0} devices!".format(len(workflow.devices)),
                   colorama.Fore.GREEN))
    if any(not x.target_page for x in workflow.devices):
        raise DeviceException("At least one of the devices has not been"
                              " properly configured, please re-run the"
                              " program with the \'configure\' option!")
    # Set up for capturing
    print("Setting up devices for capturing.")
    workflow.prepare_capture()

    print("({0}) capture | (r) retake last shot | (f) finish "
          .format("/".join(capture_keys)))
    # Start trigger loop
    _trigger_loop()

    workflow.finish_capture()


def _update_callback(_, changes):
    """ Signal handler callback that draws a step's progress. """
    if 'status' in changes and 'step_progress' in changes['status']:
        draw_progress(changes['status']['step_progress'])



def postprocess(config):
    """ Launch postprocessing plugins and display their progress

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    path = config['path'].get()
    workflow = spreads.workflow.Workflow(config=config, path=path)
    draw_progress(0.0)
    spreads.workflow.on_modified.connect(_update_callback, sender=workflow,
                                         weak=False)
    workflow.process()


def output(config):
    """ Launch output plugins and display their progress

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    path = config['path'].get()
    workflow = spreads.workflow.Workflow(config=config, path=path)
    draw_progress(0)
    spreads.workflow.on_modified.connect(_update_callback, sender=workflow,
                                         weak=False)
    workflow.output()


def wizard(config):
    """ Launch every step in succession with the same configuration.

    :param config:      Currently active global configuration
    :type config:       :py:class:`spreads.config.Configuration`
    """
    print("==========================\n",
          "Starting capturing process\n",
          "==========================")
    capture(config)

    print("=======================\n"
          "Starting postprocessing\n"
          "=======================")
    postprocess(config)

    print("=================\n",
          "Generating output\n"
          "=================")
    output(config)

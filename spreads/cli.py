# -*- coding: utf-8 -*-

# Copyright (c) 2013 Johannes Baiter. All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
spreads CLI code.
"""

from __future__ import division, unicode_literals, print_function

import argparse
import logging
import logging.handlers
import os
import sys
import time

import colorama
import pkg_resources
import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path

import spreads.plugin as plugin
from spreads.workflow import (Workflow, created as workflow_created,
                              progress as workflow_progress)
from spreads.util import (DeviceException, ColourStreamHandler,
                          add_argument_from_option)

if sys.platform == 'win32':
    import msvcrt
    getch = msvcrt.getch()
else:
    import termios
    import tty

    def getch():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        char = None
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return char


def colorize(text, color):
    return color + text + colorama.Fore.RESET


def draw_progress(progress):
    logging.debug(progress)
    width = 32
    num_bars = int(width*progress/1.0)
    sys.stdout.write('[{0}{1}] {2}%\r'.format(
        '#'*num_bars,
        ' '*(width-num_bars), int(progress*100)))
    sys.stdout.flush()


def _select_driver():
    print(colorize("Please select a device driver from the following list:",
                   colorama.Fore.BLUE))
    available_drivers = list(
        pkg_resources.iter_entry_points('spreadsplug.devices'))
    for pos, ext in enumerate(available_drivers, 1):
        print("  [{0}]: {1}".format(pos, ext.name))
    while True:
        selection = raw_input("Select a driver: ")
        if not selection.isdigit() or int(selection) > len(available_drivers):
            print(colorize("Please select a number in the range of 1 to {0}"
                           .format(len(available_drivers)), colorama.Fore.RED))
            continue
        driver = unicode(available_drivers[int(selection)-1].name)
        print(colorize("Selected \"{0}\" as device driver".format(driver),
                       colorama.Fore.GREEN))
        return driver


def _select_plugins(selected_plugins=None):
    if selected_plugins is None:
        selected_plugins = []
    print("Please select your desired plugins from the following list:")
    available_plugins = list(
        pkg_resources.iter_entry_points('spreadsplug.hooks'))
    while True:
        for pos, ext in enumerate(available_plugins, 1):
            print("  {0} {1}: {2}"
                  .format('x' if ext.name in selected_plugins else ' ',
                          pos, ext.name))
        selection = raw_input("Select a plugin (or hit enter to finish): ")
        if not selection:
            break
        if not selection.isdigit() or int(selection) > len(available_plugins):
            print(colorize("Please select a number in the range of 1 to {0}"
                           .format(len(available_plugins)), colorama.Fore.RED))
            continue
        plugin_name = available_plugins[int(selection)-1].name
        if plugin_name in selected_plugins:
            selected_plugins.remove(plugin_name)
        else:
            selected_plugins.append(plugin_name)
    return selected_plugins


def _setup_processing_pipeline(config):
    pm = plugin.get_pluginmanager(config)
    extensions = [
        ext.name for ext in
        plugin.get_relevant_extensions(pm, [plugin.ProcessHookMixin])]
    if not extensions:
        return
    print("The following postprocessing plugins were detected:")
    print("\n".join(" - {0}".format(ext) for ext in extensions))
    while True:
        answer = raw_input("Please enter the extensions in the order that they"
                           " should be invoked, separated by commas:\n")
        plugins = [x.strip() for x in answer.split(',')]
        if any(x not in extensions for x in plugins):
            print(colorize("At least one of the entered extensions was not"
                           "found, please try again!", colorama.Fore.RED))
        else:
            break
    config["plugins"] = plugins + [x for x in config["plugins"].get()
                                   if x not in plugins]


def _set_device_target_page(config, target_page):
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
    config["driver"] = _select_driver()
    config["plugins"] = _select_plugins(config["plugins"].get())

    # Set default plugin configuration
    plugin.set_default_config(config)
    _setup_processing_pipeline(config)

    cfg_path = os.path.join(config.config_dir(), confit.CONFIG_FILENAME)

    driver = plugin.get_driver(config["driver"].get()).driver

    # We only need to set the device target_page if the driver supports
    # shooting with two devices
    if plugin.DeviceFeatures.IS_CAMERA in driver.features:
        answer = raw_input(
            "Do you want to configure the target_page of your devices?\n"
            "(Required for shooting with two devices) [y/n]: ")
        answer = True if answer.lower() == 'y' else False
        if answer:
            print("Setting target page on cameras")
            for target_page in ('odd', 'even'):
                _set_device_target_page(config, target_page)

        answer = raw_input("Do you want to setup the focus for your cameras? "
                           "[y/n]: ")
        answer = True if answer.lower() == 'y' else False
        if answer:
            print("Please turn on one of your capture devices.\n"
                  "Press any key to continue")
            getch()
            devs = plugin.get_devices(config, force_reload=True)
            print("Please put a book with as little whitespace as possible"
                  "under your cameras.\nPress any button to continue")
            getch()
            focus = devs[0]._acquire_focus()
            config['device']['focus_distance'] = focus
    print("Writing configuration file to '{0}'".format(cfg_path))
    config.dump(filename=cfg_path)


def capture(config):
    # NOTE: We have to use a 1-item list to work around the lack of a
    #       'nonlocal' keyword in Python 2...
    start_time = [None]
    path = config['path'].get()
    workflow = Workflow(config=config, path=path)
    workflow_created.send(sender=workflow)
    capture_keys = workflow.config['capture']['capture_keys'].as_str_seq()

    # Some closures
    def refresh_stats():
        # Callback to print statistics
        if start_time[0] is not None:
            pages_per_hour = ((3600/(time.time() - start_time[0]))
                              * workflow.pages_shot)
        else:
            pages_per_hour = 0.0
            start_time[0] = time.time()
        status = ("\rShot {0: >3} pages [{1: >4.0f}/h] "
                  .format(unicode(workflow.pages_shot), pages_per_hour))
        sys.stdout.write(status)
        sys.stdout.flush()

    def trigger_loop():
        is_posix = sys.platform != 'win32'
        old_count = workflow.pages_shot
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
                if workflow.pages_shot != old_count:
                    old_count = workflow.pages_shot
                    refresh_stats()
                if not data_available():
                    continue
                char = read_char()
                if char in tuple(capture_keys) + ('r', ):
                    workflow.capture(retake=(char == 'r'))
                    refresh_stats()
                elif char == 'f':
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
    trigger_loop()

    workflow.finish_capture()


def postprocess(config):
    path = config['path'].get()
    workflow = Workflow(config=config, path=path)
    draw_progress(0.0)
    workflow_progress.connect(
        receiver=lambda **kwargs: draw_progress(kwargs['progress']),
        sender=workflow,
        weak=False)
    workflow.process()


def output(config):
    path = config['path'].get()
    workflow = Workflow(config=config, path=path)
    draw_progress(0)
    workflow_progress.connect(
        receiver=lambda **kwargs: draw_progress(kwargs['progress']),
        sender=workflow,
        weak=False)
    workflow.output()


def wizard(config):
    # TODO: Think about how we can make this more dynamic, i.e. get list of
    #       options for plugin with a description for each entry
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


def setup_parser(config):
    def _add_device_arguments(name, parser):
        tmpl = plugin.get_driver(config["driver"]
                                 .get()).driver.configuration_template()
        if not tmpl:
            return
        for key, option in tmpl.iteritems():
            try:
                add_argument_from_option('device', key, option, parser)
            except:
                return

    def _add_plugin_arguments(hooks, parser):
        extensions = plugin.get_relevant_extensions(pluginmanager, hooks)
        for ext in extensions:
            tmpl = ext.plugin.configuration_template()
            if not tmpl:
                continue
            for key, option in tmpl.iteritems():
                try:
                    add_argument_from_option(ext.name, key, option, parser)
                except:
                    continue

    root_options = {
        'verbose': plugin.PluginOption(value=False,
                                       docstring="Enable verbose output"),
        'logfile': plugin.PluginOption(value="~/.config/spreads/spreads.log",
                                       docstring="Path to logfile"),
        'loglevel': plugin.PluginOption(value=['info', 'critical', 'error',
                                               'warning', 'debug'],
                                        docstring="Logging level for logfile",
                                        selectable=True)
    }

    pluginmanager = plugin.get_pluginmanager(config)
    rootparser = argparse.ArgumentParser(
        description="Scanning Tool for  DIY Book Scanner")
    subparsers = rootparser.add_subparsers()
    for key, option in root_options.iteritems():
        add_argument_from_option('', key, option, rootparser)

    wizard_parser = subparsers.add_parser(
        'wizard', help="Interactive mode")
    wizard_parser.add_argument(
        "path", type=unicode, help="Project path")
    wizard_parser.set_defaults(subcommand=wizard)

    config_parser = subparsers.add_parser(
        'configure', help="Perform initial configuration")
    config_parser.set_defaults(subcommand=configure)

    capture_parser = subparsers.add_parser(
        'capture', help="Start the capturing workflow")
    capture_parser.add_argument(
        "path", type=unicode, help="Project path")
    capture_parser.set_defaults(subcommand=capture)
    # Add arguments from plugins
    for parser in (capture_parser, wizard_parser):
        _add_plugin_arguments(
            [plugin.CaptureHooksMixin, plugin.TriggerHooksMixin], parser)
        if 'driver' in config.keys():
            _add_device_arguments('capture', parser)

    postprocess_parser = subparsers.add_parser(
        'postprocess',
        help="Postprocess scanned images.")
    postprocess_parser.add_argument(
        "path", type=unicode, help="Project path")
    postprocess_parser.add_argument(
        "--jobs", "-j", dest="jobs", type=int, default=None,
        metavar="<int>", help="Number of concurrent processes")
    postprocess_parser.set_defaults(subcommand=postprocess)
    # Add arguments from plugins
    for parser in (postprocess_parser, wizard_parser):
        _add_plugin_arguments([plugin.ProcessHookMixin], parser)

    output_parser = subparsers.add_parser(
        'output',
        help="Generate output files.")
    output_parser.add_argument(
        "path", type=unicode, help="Project path")
    output_parser.set_defaults(subcommand=output)
    # Add arguments from plugins
    for parser in (output_parser, wizard_parser):
        _add_plugin_arguments([plugin.OutputHookMixin], parser)

    # Add custom subcommands from plugins
    if config["plugins"].get():
        exts = plugin.get_relevant_extensions(pluginmanager,
                                              [plugin.SubcommandHookMixin])

        for ext in exts:
            ext.plugin.add_command_parser(subparsers)
    return rootparser


def set_config_from_args(config, args):
    for argkey, value in args.__dict__.iteritems():
        if value is None or argkey == 'subcommand' or argkey.startswith('_'):
            continue
        if '.' in argkey:
            section, key = argkey.split('.')
            config[section][key] = value
        else:
            config[argkey] = value


def main():
    # Set to ERROR so we can see errors during plugin loading.
    logging.basicConfig(loglevel=logging.ERROR)

    # Lazy-load configuration
    config = confit.LazyConfig('spreads', __name__)
    # Load default plugin configuration
    plugin.set_default_config(config)
    # Load user configuration
    config.read()

    parser = setup_parser(config)
    args = parser.parse_args()
    # Set configuration from parsed arguments
    set_config_from_args(config, args)

    loglevel = config['loglevel'].as_choice({
        'none':     logging.NOTSET,
        'info':     logging.INFO,
        'debug':    logging.DEBUG,
        'warning':  logging.WARNING,
        'error':    logging.ERROR,
        'critical': logging.CRITICAL,
    })

    # Set up logger
    logger = logging.getLogger()
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    stdout_handler = ColourStreamHandler()
    stdout_handler.setLevel(logging.DEBUG if config['verbose'].get()
                            else logging.WARNING)
    stdout_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(stdout_handler)
    if 'logfile' in config.keys():
        logfile = Path(os.path.expanduser(config['logfile'].get()))
        if not logfile.parent.exists():
            logfile.parent.mkdir()
        file_handler = logging.handlers.RotatingFileHandler(
            filename=unicode(logfile), maxBytes=512*1024, backupCount=1)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(message)s [%(name)s] [%(levelname)s]"))
        file_handler.setLevel(loglevel)
        logger.addHandler(file_handler)

    logger.setLevel(logging.DEBUG)

    args.subcommand(config)

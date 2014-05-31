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
spreads CLI code.
"""

from __future__ import division, unicode_literals, print_function

import argparse
import logging
import logging.handlers
import sys
import time

import colorama
from spreads.vendor.pathlib import Path

import spreads.workflow
import spreads.plugin as plugin
from spreads.config import Configuration
from spreads.util import DeviceException, ColourStreamHandler, EventHandler

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
    width = 32
    num_bars = int(width*progress/1.0)
    sys.stdout.write('[{0}{1}] {2}%\r'.format(
        '#'*num_bars,
        ' '*(width-num_bars), int(progress*100)))
    sys.stdout.flush()


def _select_driver():
    print(colorize("Please select a device driver from the following list:",
                   colorama.Fore.BLUE))
    available_drivers = plugin.available_drivers()
    print("  [0]: None")
    for pos, ext in enumerate(plugin.available_drivers(), 1):
        print("  [{0}]: {1}".format(pos, ext))
    while True:
        selection = raw_input("Select a driver: ")
        if not selection.isdigit() or int(selection) > len(available_drivers):
            print(colorize("Please select a number in the range of 0 to {0}"
                           .format(len(available_drivers)), colorama.Fore.RED))
            continue
        if int(selection) == 0:
            return None
        driver = unicode(available_drivers[int(selection)-1])
        print(colorize("Selected \"{0}\" as device driver".format(driver),
                       colorama.Fore.GREEN))
        return driver


def _select_plugins(preselected=None):
    if preselected is None:
        selected_plugins = []
    else:
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
    exts = [name for name, cls in plugin.get_plugins(*config["plugins"].get())
            .iteritems() if issubclass(cls, plugin.ProcessHookMixin)]
    if not exts:
        return
    print("The following postprocessing plugins were detected:")
    print("\n".join(" - {0}".format(ext) for ext in exts))
    while True:
        answer = raw_input("Please enter the extensions in the order that they"
                           " should be invoked, separated by commas:\n")
        plugins = [x.strip() for x in answer.split(',')]
        if any(x not in exts for x in plugins):
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
    old_plugins = config["plugins"].get()
    driver_name = _select_driver()
    if driver_name:
        config["driver"] = driver_name
        driver = plugin.get_driver(config["driver"].get())
    else:
        driver = None
    config["plugins"] = _select_plugins(old_plugins)
    _setup_processing_pipeline(config)

    # Load default configuration for newly added plugins
    new_plugins = [x for x in config["plugins"].get() if x not in old_plugins]
    for name in new_plugins:
        if not name in config.templates:
            continue
        config.set_from_template(name, config.templates[name])

    # We only need to set the device target_page if the driver supports
    # shooting with two devices
    if driver and plugin.DeviceFeatures.IS_CAMERA in driver.features:
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
    print("Writing configuration file to '{0}'".format(config.cfg_path))
    config.dump(filename=config.cfg_path)


def capture(config):
    path = config['path'].get()
    workflow = spreads.workflow.Workflow(config=config, path=path)
    spreads.workflow.on_created.send(workflow=workflow)
    capture_keys = workflow.config['core']['capture_keys'].as_str_seq()

    # Some closures
    def refresh_stats():
        # Callback to print statistics
        if refresh_stats.start_time is not None:
            pages_per_hour = ((3600/(time.time() - refresh_stats.start_time))
                              * len(workflow.images))
        else:
            pages_per_hour = 0.0
            refresh_stats.start_time = time.time()
        status = ("\rShot {0: >3} pages [{1: >4.0f}/h] "
                  .format(len(workflow.images), pages_per_hour))
        sys.stdout.write(status)
        sys.stdout.flush()
    refresh_stats.start_time = None

    def trigger_loop():
        is_posix = sys.platform != 'win32'
        old_count = len(workflow.images)
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
                if len(workflow.images) != old_count:
                    old_count = len(workflow.images)
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
    workflow = spreads.workflow.Workflow(config=config, path=path)
    draw_progress(0.0)
    spreads.workflow.on_step_progressed.connect(
        lambda x, **kwargs: draw_progress(kwargs['progress']),
        sender=workflow, weak=False)
    workflow.process()


def output(config):
    path = config['path'].get()
    workflow = spreads.workflow.Workflow(config=config, path=path)
    draw_progress(0)
    spreads.workflow.on_step_progressed.connect(
        lambda x, **kwargs: draw_progress(kwargs['progress']),
        sender=workflow, weak=False)
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
    plugins = plugin.get_plugins(*config["plugins"].get())
    rootparser = argparse.ArgumentParser(
        description="Scanning Tool for  DIY Book Scanner")
    subparsers = rootparser.add_subparsers()
    for key, option in config.templates['core'].iteritems():
        try:
            add_argument_from_template('core', key, option, rootparser)
        except TypeError:
            continue

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
        ext_names = [
            name for name, cls in plugins.iteritems()
            if any(issubclass(cls, mixin) for mixin in
                   (plugin.CaptureHooksMixin, plugin.TriggerHooksMixin))]
        ext_names.append('driver')
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                try:
                    add_argument_from_template(ext, key, tmpl, parser)
                except TypeError:
                    continue

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
        ext_names = [name for name, cls in plugins.iteritems()
                     if issubclass(cls, plugin.ProcessHookMixin)]
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                try:
                    add_argument_from_template(ext, key, tmpl, parser)
                except TypeError:
                    continue

    output_parser = subparsers.add_parser(
        'output',
        help="Generate output files.")
    output_parser.add_argument(
        "path", type=unicode, help="Project path")
    output_parser.set_defaults(subcommand=output)
    # Add arguments from plugins
    for parser in (output_parser, wizard_parser):
        ext_names = [name for name, cls in plugins.iteritems()
                     if issubclass(cls, plugin.OutputHookMixin)]
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                try:
                    add_argument_from_template(ext, key, tmpl, parser)
                except TypeError:
                    continue

    # Add custom subcommands from plugins
    if config["plugins"].get():
        classes = (cls for cls in plugins.values()
                   if issubclass(cls, plugin.SubcommandHookMixin))
        for cls in classes:
            cls.add_command_parser(subparsers)
    return rootparser


def add_argument_from_template(extname, key, template, parser):
    flag = "--{0}".format(key.replace('_', '-'))
    default = (template.value
               if not template.selectable
               else template.value[0])
    kwargs = {'help': ("{0} [default: {1}]"
                       .format(template.docstring, default)),
              'dest': "{0}{1}".format(extname, '.'+key if extname else key)}
    if isinstance(template.value, basestring):
        kwargs['type'] = unicode
        kwargs['metavar'] = "<str>"
    elif isinstance(template.value, bool):
        kwargs['help'] = template.docstring
        if template.value:
            flag = "--no-{0}".format(key.replace('_', '-'))
            kwargs['help'] = ("Disable {0}"
                              .format(template.docstring.lower()))
            kwargs['action'] = "store_const"
            kwargs['const'] = False
        else:
            kwargs['action'] = "store_const"
            kwargs['const'] = True
    elif isinstance(template.value, float):
        kwargs['type'] = float
        kwargs['metavar'] = "<float>"
    elif isinstance(template.value, int):
        kwargs['type'] = int
        kwargs['metavar'] = "<int>"
    elif template.selectable:
        kwargs['type'] = type(template.value[0])
        kwargs['metavar'] = "<{0}>".format("/".join(template.value))
        kwargs['choices'] = template.value
    else:
        raise TypeError("Unsupported option type")
    parser.add_argument(flag, **kwargs)


def main():
    # Set to ERROR so we can see errors during plugin loading.
    logging.basicConfig(loglevel=logging.ERROR)

    config = Configuration()

    parser = setup_parser(config)
    args = parser.parse_args()
    # Set configuration from parsed arguments
    config.set_from_args(args)

    loglevel = config['core']['loglevel'].as_choice({
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
    stdout_handler.setLevel(logging.DEBUG if config['core']['verbose'].get()
                            else logging.WARNING)
    stdout_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(stdout_handler)
    logger.addHandler(EventHandler())
    if 'logfile' in config.keys():
        logfile = Path(config['core']['logfile'].as_filename())
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

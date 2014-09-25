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
Core logic for application startup and parsing of command-line arguments
"""

from __future__ import division, unicode_literals, print_function

import argparse
import logging
import logging.handlers
import os
import sys
import traceback

import colorama
from spreads.vendor.confit import ConfigError
from spreads.vendor.pathlib import Path

import spreads.cli as cli
import spreads.plugin as plugin
import spreads.util as util
from spreads.config import Configuration


def add_argument_from_template(extname, key, template, parser, current_val):
    """ Add option from `template` to `parser` under the name `key`.

    Templates with a boolean value type will create a `--<key>` or
    `--no-<key>` flag, depending on their current value.

    :param extname:     Name of the configuration section this option's result
                        should be stored in
    :param key:         Configuration key in section, will also determine the
                        name of the argument.
    :param template:    Template for the argument
    :type template:     :py:class:`spreads.config.OptionTemplate`
    :param parser:      Argument parser the argument should be added to
    :type parser:       :py:class:`argparse.ArgumentParser`
    :param current_val: Current value of the option
    """
    flag = "--{0}".format(key.replace('_', '-'))
    default = current_val
    kwargs = {'help': ("{0} [default: {1}]"
                       .format(template.docstring, default)),
              'dest': "{0}{1}".format(extname, '.'+key if extname else key)}
    if isinstance(template.value, basestring) or template.value is None:
        kwargs['type'] = unicode
        kwargs['metavar'] = "<str>"
    elif isinstance(template.value, bool):
        kwargs['help'] = template.docstring
        if current_val:
            flag = "--no-{0}".format(key.replace('_', '-'))
            kwargs['help'] = ("Disable {0}"
                              .format(template.docstring.lower()))
            kwargs['action'] = "store_false"
        else:
            kwargs['action'] = "store_true"
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


def should_show_argument(template, active_plugins):
    """ Checks the :py:attr:`spreads.config.OptionTemplate.depends` attribute
    for dependencies on other plugins and validates them against the list of
    activated plugins.

    We do not validate dependencies on other configuration settings because
    we don't have access to the final state of the configuration at this time,
    since the configuration can potentially be changed by other command-line
    flags.

    :param template:        Template to check
    :type template:         :py:class:`spreads.config.OptionTemplate`
    :param active_plugins:  List of names of activated plugins
    :returns:               Whether or not the argument should be displayed
    """
    if template.depends is None or type(template.depends) == dict:
        return True
    else:
        return template.depends in active_plugins


def setup_parser(config):
    """ Sets up an :py:class:`argparse.ArgumentParser` instance with all
    options and subcommands that are available in the core and activated
    plugins.

    :param config:  Current application configuration
    :type config:   :py:class:`spreads.config.Configuration`
    :returns:       Fully initialized argument parser
    :rtype:         :py:class:`argparse.ArgumentParser`
    """
    plugins = plugin.get_plugins(*config["plugins"].get())

    def _add_arguments(parsers, mixins, extra_names=None):
        if extra_names is None:
            extra_names = []
        for parser in parsers:
            # Only plugins that implement the capture or trigger hook mixins
            # and the currently active device configuration are relevant for
            # this subcommand.
            ext_names = [name for name, cls in plugins.iteritems()
                         if any(issubclass(cls, mixin) for mixin in mixins)]
            ext_names.extend(extra_names)
            for ext in ext_names:
                for key, tmpl in config.templates.get(ext, {}).iteritems():
                    if not should_show_argument(option,
                                                config['plugins'].get()):
                        continue
                    try:
                        add_argument_from_template(ext, key, tmpl, parser,
                                                   config[ext][key].get())
                    except TypeError:
                        continue

    rootparser = argparse.ArgumentParser(
        description="Scanning Tool for  DIY Book Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    rootparser.add_argument(
        '-V', '--version', action='version',
        version=(
            "spreads {0}\n\n"
            "Licensed under the terms of the GNU Affero General Public "
            "License 3.0.\n"
            "(C) 2013-2014 Johannes Baiter <johannes.baiter@gmail.com>\n"
            "For a complete list of contributors see:\n"
            "https://github.com/DIYBookScanner/spreads/graphs/contributors\n\n"
            .format(util.get_version())))

    for key, option in config.templates['core'].iteritems():
        if not should_show_argument(option, config['plugins'].get()):
            continue
        try:
            add_argument_from_template('core', key, option, rootparser,
                                       config['core'][key].get())
        except TypeError:
            continue

    subparsers = rootparser.add_subparsers()

    wizard_parser = subparsers.add_parser(
        'wizard', help="Interactive mode")
    wizard_parser.add_argument(
        "path", type=unicode, help="Project path")
    wizard_parser.set_defaults(subcommand=cli.wizard)

    config_parser = subparsers.add_parser(
        'configure', help="Perform initial configuration")
    config_parser.set_defaults(subcommand=cli.configure)

    try:
        import spreads.tkconfigure as tkconfigure
        guiconfig_parser = subparsers.add_parser(
            'guiconfigure', help="Perform initial configuration with a GUI")
        guiconfig_parser.set_defaults(subcommand=tkconfigure.configure)
    except ImportError:
        pass

    capture_parser = subparsers.add_parser(
        'capture', help="Start the capturing workflow")
    capture_parser.add_argument(
        "path", type=unicode, help="Project path")
    capture_parser.set_defaults(subcommand=cli.capture)
    # Add arguments from plugins
    _add_arguments(parsers=(capture_parser, wizard_parser),
                   mixins=(plugin.CaptureHooksMixin, plugin.TriggerHooksMixin),
                   extra_names=('device',))

    postprocess_parser = subparsers.add_parser(
        'postprocess',
        help="Postprocess scanned images.")
    postprocess_parser.add_argument(
        "path", type=unicode, help="Project path")
    postprocess_parser.add_argument(
        "--jobs", "-j", dest="jobs", type=int, default=None,
        metavar="<int>", help="Number of concurrent processes")
    postprocess_parser.set_defaults(subcommand=cli.postprocess)
    _add_arguments(parsers=(postprocess_parser, wizard_parser),
                   mixins=(plugin.ProcessHooksMixin,))

    output_parser = subparsers.add_parser(
        'output',
        help="Generate output files.")
    output_parser.add_argument(
        "path", type=unicode, help="Project path")
    output_parser.set_defaults(subcommand=cli.output)
    _add_arguments(parsers=(output_parser, wizard_parser),
                   mixins=(plugin.OutputHooksMixin,))

    # Add custom subcommands from plugins
    if config["plugins"].get():
        classes = (cls for cls in plugins.values()
                   if issubclass(cls, plugin.SubcommandHooksMixin))
        for cls in classes:
            cls.add_command_parser(subparsers, config)
    return rootparser


def setup_logging(config):
    """ Conigure application-wide logger.

    :param config:  Global configuration
    :type config:   :py:class:`spreads.config.Configuration`
    """
    loglevel = config['core']['loglevel'].as_choice({
        'none':     logging.NOTSET,
        'info':     logging.INFO,
        'debug':    logging.DEBUG,
        'warning':  logging.WARNING,
        'error':    logging.ERROR,
        'critical': logging.CRITICAL,
    })
    logger = logging.getLogger()
    # Remove previous handlers
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    # Add stderr handler
    if util.is_os('windows'):
        stdout_handler = logging.StreamHandler()
    else:
        stdout_handler = util.ColourStreamHandler()
    stdout_handler.setLevel(logging.DEBUG if config['core']['verbose'].get()
                            else logging.WARNING)
    stdout_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logger.addHandler(stdout_handler)

    # Add event handler
    logger.addHandler(util.EventHandler())

    # Add logfile handler
    logfile = Path(config['core']['logfile'].as_filename())
    if not logfile.parent.exists():
        logfile.parent.mkdir()
    file_handler = logging.handlers.RotatingFileHandler(
        filename=unicode(logfile), maxBytes=512*1024, backupCount=1)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(message)s [%(name)s] [%(levelname)s]"))
    file_handler.setLevel(loglevel)
    logger.addHandler(file_handler)

    # Set root logger level (needed for web plugin)
    logger.setLevel(logging.DEBUG)


def run_config_windows():
    """ Entry point to launch graphical configuration dialog on Windows. """
    # Needed so that .exe files in Program Files can be launched.
    os.environ['PATH'] += (";" + os.environ['PROGRAMFILES'])
    config = Configuration()
    setup_logging(config)
    from spreads.tkconfigure import configure
    configure(config)


def run_service_windows():
    """ Entry point to launch web plugin server on Windows. """
    # Needed so that .exe files in Program Files can be launched.
    os.environ['PATH'] += (";" + os.environ['PROGRAMFILES'])
    config = Configuration()
    config['core']['loglevel'] = 'debug'
    if not config['plugins'].get():
        config['plugins'] = ['autorotate', 'scantailor', 'tesseract',
                             'pdfbeads', 'web']
        config.load_defaults(overwrite=False)
    setup_logging(config)
    from spreadsplug.web import run_windows_service
    config['web']['mode'] = 'processor'
    run_windows_service(config)


def run():
    """ Setup the application and run subcommand"""
    config = Configuration()
    parser = setup_parser(config)
    args = parser.parse_args()
    config.set_from_args(args)
    setup_logging(config)
    args.subcommand(config)


def main():
    """ Entry point for `spread` command-line application. """
    # Initialize color support
    colorama.init()
    print_error = lambda x: print(util.colorize(x, colorama.Fore.RED),
                                  file=sys.stderr)
    try:
        run()
    except util.DeviceException as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print_error("There is a problem with your device configuration:")
        print_error(e.message)
    except ConfigError as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print_error("There is a problem with your configuration file(s):")
        print_error(e.message)
    except util.MissingDependencyException as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print_error("You are missing a dependency for one of your "
                    "enabled plugins:")
        print_error(e.message)
    except KeyboardInterrupt:
        colorama.deinit()
        sys.exit(1)
    except Exception as e:
        typ, val, tb = sys.exc_info()
        print_error("spreads encountered an error:")
        print_error("".join(traceback.format_exception(typ, val, tb)))
    # Deinitialize color support
    colorama.deinit()


if __name__ == '__main__':
    logging.basicConfig(loglevel=logging.ERROR)
    main()

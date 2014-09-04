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
    flag = "--{0}".format(key.replace('_', '-'))
    default = current_val
    kwargs = {'help': ("{0} [default: {1}]"
                       .format(template.docstring, default)),
              'dest': "{0}{1}".format(extname, '.'+key if extname else key)}
    if isinstance(template.value, basestring):
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
    """ Checks for an OptionTemplate's `depends` attribute for dependencies
        on other plugins and validates them against the list of activated
        plugins.
    """
    if template.depends is None or type(template.depends) == dict:
        return True
    else:
        return template.depends in active_plugins


def setup_parser(config):
    plugins = plugin.get_plugins(*config["plugins"].get())
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
        print "Could not load _tkinter module, disabling guiconfigure command"

    capture_parser = subparsers.add_parser(
        'capture', help="Start the capturing workflow")
    capture_parser.add_argument(
        "path", type=unicode, help="Project path")
    capture_parser.set_defaults(subcommand=cli.capture)
    # Add arguments from plugins
    for parser in (capture_parser, wizard_parser):
        ext_names = [
            name for name, cls in plugins.iteritems()
            if any(issubclass(cls, mixin) for mixin in
                   (plugin.CaptureHooksMixin, plugin.TriggerHooksMixin))]
        ext_names.append('device')
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                if not should_show_argument(option, config['plugins'].get()):
                    continue
                try:
                    add_argument_from_template(ext, key, tmpl, parser,
                                               config[ext][key].get())
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
    postprocess_parser.set_defaults(subcommand=cli.postprocess)
    # Add arguments from plugins
    for parser in (postprocess_parser, wizard_parser):
        ext_names = [name for name, cls in plugins.iteritems()
                     if issubclass(cls, plugin.ProcessHookMixin)]
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                if not should_show_argument(option, config['plugins'].get()):
                    continue
                try:
                    add_argument_from_template(ext, key, tmpl, parser,
                                               config[ext][key].get())
                except TypeError:
                    continue

    output_parser = subparsers.add_parser(
        'output',
        help="Generate output files.")
    output_parser.add_argument(
        "path", type=unicode, help="Project path")
    output_parser.set_defaults(subcommand=cli.output)
    # Add arguments from plugins
    for parser in (output_parser, wizard_parser):
        ext_names = [name for name, cls in plugins.iteritems()
                     if issubclass(cls, plugin.OutputHookMixin)]
        for ext in ext_names:
            for key, tmpl in config.templates.get(ext, {}).iteritems():
                if not should_show_argument(option, config['plugins'].get()):
                    continue
                try:
                    add_argument_from_template(ext, key, tmpl, parser,
                                               config[ext][key].get())
                except TypeError:
                    continue

    # Add custom subcommands from plugins
    if config["plugins"].get():
        classes = (cls for cls in plugins.values()
                   if issubclass(cls, plugin.SubcommandHookMixin))
        for cls in classes:
            cls.add_command_parser(subparsers, config)
    return rootparser


def setup_logging(config):
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
    os.environ['PATH'] += (";" + os.environ['PROGRAMFILES'])
    config = Configuration()
    setup_logging(config)
    from spreads.tkconfigure import configure
    configure(config)


def run_service_windows():
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
    config = Configuration()

    parser = setup_parser(config)
    args = parser.parse_args()
    # Set configuration from parsed arguments
    config.set_from_args(args)

    setup_logging(config)

    # Run subcommand
    args.subcommand(config)


def main():
    # Initialize color support
    colorama.init()
    try:
        run()
    except util.DeviceException as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print(colorama.Fore.RED + "There is a problem with your device"
                                  " configuration:")
        print(colorama.Fore.RED + e.message)
    except ConfigError as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print(colorama.Fore.RED +
              "There is a problem with your configuration file(s):")
        print(colorama.Fore.RED + e.message)
    except util.MissingDependencyException as e:
        typ, val, tb = sys.exc_info()
        logging.debug("".join(traceback.format_exception(typ, val, tb)))
        print(colorama.Fore.RED +
              "You are missing a dependency for one of your enabled plugins:")
        print(colorama.Fore.RED + e.message)
    except KeyboardInterrupt:
        colorama.deinit()
        sys.exit(1)
    except Exception as e:
        typ, val, tb = sys.exc_info()
        print(colorama.Fore.RED + "spreads encountered an error:")
        print(colorama.Fore.RED +
              "".join(traceback.format_exception(typ, val, tb)))
    # Deinitialize color support
    colorama.deinit()


if __name__ == '__main__':
    logging.basicConfig(loglevel=logging.ERROR)
    main()

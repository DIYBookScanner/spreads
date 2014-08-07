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

from __future__ import division, unicode_literals

import abc
import logging
from collections import OrderedDict

import pkg_resources
from blinker import Namespace

from spreads.config import OptionTemplate
from spreads.util import (abstractclassmethod, DeviceException,
                          MissingDependencyException)


logger = logging.getLogger("spreads.plugin")
devices = None
extensions = dict()


class ExtensionException(Exception):
    def __init__(self, message=None, extension=None):
        super(ExtensionException, self).__init__(message)
        self.extension = extension


class SpreadsPlugin(object):  # pragma: no cover
    """ Plugin base class.

    """
    signals = Namespace()
    on_progressed = signals.signal('plugin:progressed', doc="""\
    Sent by a :class:`SpreadsPlugin` when it has progressed in a long-running
    operation.

    :argument :class:`SpreadsPlugin`:   the SpreadsPlugin that progressed
    :keyword float progress:            the progress as a value between 0 and 1
    """)

    @classmethod
    def configuration_template(cls):
        """ Allows a plugin to define its configuration keys.

        The returned dictionary has to be flat (i.e. no nested dicts)
        and contain a OptionTemplate object for each key.

        Example::

          {
           'a_setting': OptionTemplate(value='default_value'),
           'another_setting': OptionTemplate(value=[1, 2, 3],
                                           docstring="A list of things"),
           # In this case, 'full-fat' would be the default value
           'milk': OptionTemplate(value=('full-fat', 'skim'),
                                docstring="Type of milk",
                                selectable=True),
          }

        :return: dict with unicode: OptionTemplate(value, docstring, selection)
        """
        pass

    def __init__(self, config):
        """ Initialize the plugin.

        :param config: The global configuration object, by default only the
                       section with plugin-specific values gets stored in
                       the `config` attribute, if the plugin has a `__name__`
                       attribute.
        :type config: confit.ConfigView

        """
        if hasattr(self, '__name__'):
            self.config = config[self.__name__]
        else:
            self.config = config


class DeviceFeatures(object):  # pragma: no cover
    #: Device can grab a preview picture
    PREVIEW = 1

    #: Device class allows the operation of two devices simultaneously
    #: (mainly to be used by cameras, where each device is responsible for
    #: capturing a single page.
    IS_CAMERA = 2


class DevicePlugin(SpreadsPlugin):  # pragma: no cover
    """ Base class for devices.

        Subclass to implement support for different devices.

    """
    __metaclass__ = abc.ABCMeta

    #: Tuple of :py:class:`DeviceFeatures` constants that designate the
    #: features the device offers.
    features = ()

    @classmethod
    def configuration_template(cls):
        if DeviceFeatures.IS_CAMERA in cls.features:
            return {
                "parallel_capture": OptionTemplate(
                    value=True,
                    docstring="Trigger capture on multiple devices at once.",
                    selectable=False),
                "flip_target_pages": OptionTemplate(
                    value=False,
                    docstring="Temporarily switch target pages (useful for "
                              "e.g. East-Asian books)")
            }

    @abstractclassmethod
    def yield_devices(cls, config):
        """ Search for usable devices, yield one at a time

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        """
        raise NotImplementedError

    def __init__(self, config, device):
        """ Set connection information and other properties.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  USB device to use for the object
        :type device:   `usb.core.Device <http://github.com/walac/pyusb>`_

        """
        self.config = config
        self._device = device

    @abc.abstractmethod
    def connected(self):
        """ Check if the device is still connected.

        :rtype:     bool

        """
        raise NotImplementedError

    def set_target_page(self, target_page):
        """ Set the device target page, if applicable.

        :param target_page: The target page
        :type target_page:  unicode in (u"odd", u"even")

        """
        raise NotImplementedError

    @abc.abstractmethod
    def prepare_capture(self, path):
        """ Prepare device for scanning.

        What this means exactly is up to the implementation and the type,
        of device, usually it involves things like switching into record
        mode, path and applying all relevant settings.

        :param path:    Project base path
        :type path:     pathlib.Path

        """
        raise NotImplementedError

    @abc.abstractmethod
    def capture(self, path):
        """ Capture a single image with the device.

        :param path:    Path for the image
        :type path:     pathlib.Path

        """
        raise NotImplementedError

    @abc.abstractmethod
    def finish_capture(self):
        """ Tell device to finish capturing.

        What this means exactly is up to the implementation and the type of
        device, with a camera it could e.g. involve retractingthe lense.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_configuration(self, updated):
        """ Update the device configuration.

        :param updated:     Updated configuration values
        :type updated:      dict
        """
        raise NotImplementedError


class HookPlugin(SpreadsPlugin):
    """ Base class for HookPlugins.

    Implement one of the available mixin classes to register for the
    appropriate hooks.

    """
    pass


class SubcommandHookMixin(object):
    __metaclass__ = abc.ABCMeta

    @abstractclassmethod
    def add_command_parser(cls, rootparser, config):
        """ Allows a plugin to register a new command with the command-line
            parser. The subparser that is added to :param rootparser: should
            set the class' ``__call__`` method as the ``func`` (via
            ``set_defaults``) that is executed when the subcommand is specified
            on the CLI.

        :param rootparser: The root parser that this plugin should add a
                           subparser to.
        :type rootparser:  argparse.ArgumentParser
        :param config:     The application configuration
        :type config:      Configuration

        """
        pass


class CaptureHooksMixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def prepare_capture(self, devices, path):
        """ Perform some action before capturing begins.

        :param devices:     The devices used for capturing
        :type devices:      list(DevicePlugin)
        :param path:        Project path
        :type path:         pathlib.Path

        """
        pass

    @abc.abstractmethod
    def capture(self, devices, path):
        """ Perform some action after each successful capture.

        :param devices:     The devices used for capturing
        :type devices:      list(DevicePlugin)
        :param path:        Project path
        :type path:         pathlib.Path

        """
        pass

    @abc.abstractmethod
    def finish_capture(self, devices, path):
        """ Perform some action after capturing has finished.

        :param devices:     The devices used for capturing
        :type devices:      list(DevicePlugin)
        :param path:        Project path
        :type path:         pathlib.Path

        """
        pass


class TriggerHooksMixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def start_trigger_loop(self, capture_callback):
        """ Start a thread that runs an event loop and periodically triggers
            a capture by calling the `capture_callback`.

        :param capture_callback:    The function to run for triggering a
                                    capture
        :type capture_callback:     function

        """
        pass

    @abc.abstractmethod
    def stop_trigger_loop(self):
        """ Stop the thread started by `start_trigger_loop*.

        """
        pass


class ProcessHookMixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def process(self, pages, target_path):
        """ Perform one or more actions that either modify the captured images
            or generate a different output.

        :param pages:       Pages to be processed
        :type pages:        list of Page objects
        :param target_path: Target directory for processed files
        :type target_path:  pathlib.Path

        """
        pass


class OutputHookMixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def output(self, pages, target_path, metadata, table_of_contents):
        """ Assemble an output file from the pages.

        :param pages:       Project path
        :type pages:        list of Page objects
        :param target_path: Target directory for processed files
        :type target_path:  pathlib.Path
        :param metadata:    Metadata for workflow
        :type metadata:     bagit.BagInfo
        :param table_of_contents: Table of Contents for workflow
        :type table_of_contents: list(TocEntry)

        """
        pass


def available_plugins():
    return sorted([ext.name for ext in
                   pkg_resources.iter_entry_points('spreadsplug.hooks')])


def get_plugins(*names):
    global extensions
    plugins = OrderedDict()
    for name in names:
        if name in extensions:
            plugins[name] = extensions[name]
            continue
        try:
            logger.debug("Looking for extension \"{0}\"".format(name))
            ext = next(pkg_resources.iter_entry_points('spreadsplug.hooks',
                                                       name=name))
        except StopIteration:
            raise ExtensionException("Could not locate extension '{0}'"
                                     .format(name), name)
        try:
            plugin = ext.load()
            plugins[name] = plugin
            extensions[name] = plugin
        except ImportError as err:
            message = err.message
            if message.startswith('No module named'):
                message = message[16:]
            raise ExtensionException(
                "Missing Python dependency for extension '{0}': {1}"
                .format(name, message, name))
        except MissingDependencyException as err:
            raise ExtensionException(
                "Error while locating external application dependency for "
                "extension '{0}':\n{1}".format(err.message, name))
    return plugins


def available_drivers():
    return [ext.name
            for ext in pkg_resources.iter_entry_points('spreadsplug.devices')]


def get_driver(driver_name):
    try:
        ext = next(pkg_resources.iter_entry_points('spreadsplug.devices',
                                                   name=driver_name))
    except StopIteration:
        raise ExtensionException("Could not locate driver '{0}'"
                                 .format(driver_name), driver_name)
    try:
        return ext.load()
    except ImportError as err:
        raise ExtensionException(
            "Missing dependency for driver '{0}': {1}"
            .format(driver_name, err.message[16:]), driver_name)


def get_devices(config, force_reload=False):
    """ Initialize configured devices.
    """
    global devices
    if not devices or force_reload:
        if 'driver' not in config.keys():
            raise DeviceException(
                "No driver has been configured\n"
                "Please run `spread configure` to select a driver.")
        driver = get_driver(config["driver"].get())
        logger.debug("Finding devices for driver \"{0}\""
                     .format(driver.__name__))
        devices = list(driver.yield_devices(config['device']))
        if not devices:
            raise DeviceException("Could not find any compatible devices!")
    return devices

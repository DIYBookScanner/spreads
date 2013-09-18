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

from __future__ import division, unicode_literals

import abc
import itertools
import logging

import usb
import stevedore
from stevedore.extension import ExtensionManager
from stevedore.named import NamedExtensionManager


import spreads
from spreads.util import abstractclassmethod, DeviceException

logger = logging.getLogger("spreads.plugin")


class PluginOption(object):
    """ A configuration option.

    :attr value:      The default value for the option or a list of available
                      options if :attr selectable: is True
    :type value:      object (or list/tuple when :attr selectable: is True)
    :attr docstring:  A string explaining the configuration option
    :type docstring:  unicode
    :attr selectable: Make the PluginOption a selectable, i.e. value contains
                      a list or tuple of acceptable values for this option,
                      with the first member being the default selection.
    :type selectable: bool
    """

    def __init__(self, value, docstring=None, selectable=False):
        self.value = value
        self.docstring = docstring
        self.selectable = selectable


class SpreadsNamedExtensionManager(NamedExtensionManager):
    """ Custom extension manager for spreads.

    stevedore's NamedExtensionmanger does not give us the Exception that caused
    a plugin to fail at initialization. This derived class throws the original
    exception instead of logging it.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = (super(SpreadsNamedExtensionManager, cls)
                             .__new__(cls, *args, **kwargs))
        return cls._instance

    def _load_plugins(self, invoke_on_load, invoke_args, invoke_kwds):
        extensions = []
        for ep in self._find_entry_points(self.namespace):
            stevedore.LOG.debug('found extension %r', ep)
            ext = self._load_one_plugin(ep,
                                        invoke_on_load,
                                        invoke_args,
                                        invoke_kwds,
                                        )
            if ext:
                extensions.append(ext)
        return extensions


class SpreadsPlugin(object):
    """ Plugin base class.

    """

    @classmethod
    def add_arguments(cls, command, parser):
        """ Allows a plugin to register new arguments with the command-line
            parser.

        :param command: The command to be modified
        :type command: unicode
        :param parser: The parser that can be modified
        :type parser: argparse.ArgumentParser

        """
        pass

    @classmethod
    def configuration_template(cls):
        """ Allows a plugin to define its configuration keys.

        The returned dictionary has to be flat (i.e. no nested dicts)
        and contain a PluginOption object for each key.

        Example:
          {
           'a_setting': PluginOption(value='default_value'),
           'another_setting': PluginOption(value=[1, 2, 3],
                                           docstring="A list of things"),
           # In this case, 'full-fat' would be the default value
           'milk': PluginOption(value=('full-fat', 'skim'),
                                docstring="Type of milk",
                                selectable=True),
          }

        :return: dict with unicode: (value, docstring, selection)
        """
        pass

    def __init__(self, config):
        """ Initialize the plugin.

        :param config: The global configuration object
        :type config: confit.ConfigView

        """
        self.config = config


class DevicePlugin(SpreadsPlugin):
    """ Base class for devices.

        Subclass to implement support for different devices.

    """
    __metaclass__ = abc.ABCMeta

    @abstractclassmethod
    def match(cls, usbdevice):
        """ Match device against USB device information.

        :param device:      The USB device to match against
        :type vendor_id:    `usb.core.Device <http://github.com/walac/pyusb>`_
        :return:            True if the :param usbdevice: matches the
                            implemented category

        """
        raise NotImplementedError

    def __init__(self, config, device):
        """ Set connection information and other properties.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  USB device to use for the object
        :type device:   `usb.core.Device <http://github.com/walac/pyusb>`_

        """
        super(DevicePlugin, self).__init__(config['device'])
        self._device = device

    def set_orientation(self, orientation):
        """ Set the device orientation, if applicable.

        :param orientation: The orientation name
        :type orientation:  unicode in (u"left", u"right")

        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_files(self):
        """ List all files on the device.

        :return: list() - The files on the device

        """
        raise NotImplementedError

    @abc.abstractmethod
    def download_files(self, local_path):
        """ Download all files from the device.

        :param local_path:  The destination path for the downloaded files
        :type local_path:   unicode

        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_files(self):
        """ Delete all files from the device.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def prepare_capture(self):
        """ Prepare device for scanning.

            What this means exactly is up to the implementation and the type,
            of device, usually it involves things like switching into record
            mode and applying all relevant settings.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def capture(self):
        """ Capture a single image with the device.

        """
        raise NotImplementedError


class HookPlugin(SpreadsPlugin):
    """ Add functionality to any of spreads' commands by implementing one or
        more of the available hooks.

    """
    @classmethod
    def add_command_parser(cls, rootparser):
        """ Allows a plugin to register a new command with the command-line
            parser. The subparser that is added to :param rootparser: should
            set the class' ``__call__`` method as the ``func`` (via
            ``set_defaults``) that is executed when the subcommand is specified
            on the CLI.

        :param rootparser: The root parser that this plugin should add a
                           subparser to.
        :type rootparser:  argparse.ArgumentParser

        """
        pass

    def prepare_capture(self, devices):
        """ Perform some action before capturing begins.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)

        """
        pass

    def capture(self, devices):
        """ Perform some action after each successful capture.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)

        """
        pass

    def finish_capture(self, devices):
        """ Perform some action after capturing has finished.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)

        """
        pass

    def download(self, devices, path):
        """ Perform some action after download from devices has finished.

            Retains all of the original information (i.e: rotation,
            metadata annotations).

        :param devices: The devices that were downloaded from.
        :type devices: list(DevicePlugin)
        :param path: The destination directory for the downloads
        :type path: unicode

        """
        pass

    def delete(self, devices):
        """ Perform some action after images have been deleted from the
            devices.

        :param devices: The devices that were downloaded from.
        :type devices: list(DevicePlugin)

        """
        pass

    def process(self, path):
        """ Perform one or more actions that either modify the captured images
            or generate a different output.

        .. note:
            This method is intended to operate on the *done* subdfolder of
            the project directory. At the beginning of postprocessing, it
            will contain copies of the images in *raw*. This is to ensure that
            a copy of the original, scanned images will always be available
            for archival purposes.

        :param path: The project path
        :type path: unicode

        """
        pass

    def output(self, path):
        """ Assemble an output file from the postprocessed images.

        .. note:
            This method is intended to take its input files from the *done*
            subfolder of the project path and store its output in the
            *out* subfolder.

        :param path: The project path
        :type path: unicode
        """
        pass


# Load drivers for all supported devices
def get_devicemanager():
    logger.debug("Creating device manager")
    return ExtensionManager(namespace='spreadsplug.devices')


def get_pluginmanager():
    logger.debug("Creating plugin manager")
    pluginmanager = SpreadsNamedExtensionManager(
        namespace='spreadsplug.hooks',
        names=spreads.config['plugins'].as_str_seq(),
        invoke_on_load=True,
        invoke_args=[spreads.config],
        name_order=True)
    return pluginmanager


def _match_device(extension, device):
    try:
        devname = usb.util.get_string(device, 256, 2)
    except:
        devname = "{0}:{1}".format(device.bus, device.address)
    logger.debug("Trying to match device \"{0}\" with plugin {1}"
                 .format(devname, extension.plugin.__name__))
    try:
        match = extension.plugin.match(device)
    # Ignore devices that don't implement `match`
    except TypeError:
        logger.debug("Plugin did not implement match method!")
        return
    if match:
        logger.debug("Plugin matched device!")
        return extension, device


def _get_device_extension_matches():
    logger.debug("Detecting support for attached devices")
    candidates = usb.core.find(find_all=True)
    devicemanager = get_devicemanager()
    for device in candidates:
        matches = filter(None, devicemanager.map(_match_device, device))
        # FIXME: Make this more robust: What if, for instance, two plugins
        #        are found for a device, one of which inherits from the other?
        if matches:
            yield matches[0]


def get_devices():
    """ Detect all attached devices and select a fitting driver.

    :returns:  list(DevicePlugin) -- All supported devices that were detected

    """
    devices = []
    for ext, device in _get_device_extension_matches():
        devices.append(ext.plugin(spreads.config, device))
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    return devices


def setup_plugin_config():
    pluginmanager = get_pluginmanager()
    device_extensions = (x[0] for x in _get_device_extension_matches())
    for ext in itertools.chain(pluginmanager, device_extensions):
        logger.debug("Obtaining configuration template for plugin \"{0}\""
                     .format(ext.name))
        tmpl = ext.plugin.configuration_template()
        if not tmpl:
            continue
        # Check if we already have a configuration entry for this plugin
        if not ext.name in spreads.config.keys():
            logging.info("Adding configuration for plugin {0}"
                         .format(ext.name))
            # Add default values
            for key, option in tmpl.items():
                if option.selectable:
                    spreads.config[ext.name][key] = option.value[0]
                else:
                    spreads.config[ext.name][key] = option.value

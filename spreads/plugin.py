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
import logging
import re
import subprocess

import usb
from stevedore.extension import ExtensionManager
from stevedore.named import NamedExtensionManager


import spreads
from spreads.util import (abstractclassmethod, find_in_path, SpreadsException,
                          DeviceException)



class SpreadsPlugin(object):
    """ Plugin base class.

    """

    #: The config key to be used for the plugin.  Plugins must set this
    #: attribute or else it will not be found. (type: *unicode*)
    # TODO: Auto-determine this from each plugin's `__name__`
    config_key = None

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
    def delete_files(self):
        """ Delete all files from device. """
        raise NotImplementedError

    @abc.abstractmethod
    def download_files(self, path):
        """ Download all files from device.

        :param path:  The destination path for the downloaded images
        :type path:   unicode

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
    def prepare_capture(self, devices):
        """ Perform some action before capturing begins.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)

        """
        pass

    def capture(self, devices, count, time):
        """ Perform some action after each successful capture.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since capturing began
        :type time: time.timedelta

        """
        pass

    def finish_capture(self, devices, count, time):
        """ Perform some action after capturing has finished.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since capturing began
        :type time: time.timedelta

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

        :param path: The project path
        :type path: unicode

        """
        pass

# Load drivers for all supported devices
devicemanager = ExtensionManager(namespace='spreadsplug.devices')
pluginmanager = NamedExtensionManager('spreadsplug.hooks',
        names=spreads.config['plugins'].as_str_seq(),
        invoke_on_load=True,
        invoke_args=[spreads.config],
        name_order=True)

def get_devices():
    """ Detect all attached devices and select a fitting driver.

    :returns:  list(DevicePlugin) -- All supported devices that were detected

    """
    def match(extension, device):
        try:
            match = extension.plugin.match(device)
        # Ignore devices that don't implement `match`
        except TypeError:
            return
        if match:
            return extension.plugin
    devices = []
    candidates = usb.core.find(find_all=True)
    for device in candidates:
        matches = filter(None, devicemanager.map(match, device))

        # FIXME: Make this more robust: What if, for instance, two plugins
        #        are found for a device, one of which inherits from the other?
        if matches:
            devices.append(matches[0](spreads.config, device))
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    return devices

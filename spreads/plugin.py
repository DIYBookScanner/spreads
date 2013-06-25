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

import logging
import re
import subprocess

import usb


import spreads
from spreads.util import find_in_path, SpreadsException


class SpreadsPlugin(object):
    """ Plugin base class.

    """

    #: The config key to be used for the plugin.  Plugins must set this
    #: attribute or else it will not be found. (type: *unicode*)
    # TODO: Auto-determine this from each plugin's `__name__`
    config_key = None

    @classmethod
    def add_arguments(cls, parser):
        """ Allows a plugin to register new arguments with the command-line
            parser.

        :param parser: The parser that can be modified
        :type parser: argparse.ArgumentParser

        """
        pass

    def __init__(self, config):
        """ Initialize the plugin.

        :param config: The global configuration object
        :type config: confit.ConfigView

        """
        if self.config_key:
            self.parent_config = config
            self.config = config[self.config_key]
        else:
            self.config = config


class DevicePlugin(SpreadsPlugin):
    """ Base class for devices.

        Subclass to implement support for different devices.

    """
    @classmethod
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

    def delete_files(self):
        """ Delete all files from device. """
        raise NotImplementedError

    def download_files(self, path):
        """ Download all files from device.

        :param path:  The destination path for the downloaded images
        :type path:   unicode

        """
        raise NotImplementedError

    def prepare_capture(self):
        """ Prepare device for scanning.

            What this means exactly is up to the implementation and the type,
            of device, usually it involves things like switching into record
            mode and applying all relevant settings.

        """
        raise NotImplementedError

    def capture(self):
        """ Capture a single image with the device.

        """
        raise NotImplementedError


class CapturePlugin(SpreadsPlugin):
    """ Add functionality to *capture* command.

    """
    def __init__(self, config):
        super(CapturePlugin, self).__init__(config['capture'])

    def prepare(self, devices):
        """ Perform some action before capturing begins.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)

        """
        raise NotImplementedError

    def capture(self, devices, count, time):
        """ Perform some action after each successful capture.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since capturing began
        :type time: time.timedelta

        """
        raise NotImplementedError

    def finish(self, devices, count, time):
        """ Perform some action after capturing has finished.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since capturing began
        :type time: time.timedelta

        """
        raise NotImplementedError


class DownloadPlugin(SpreadsPlugin):
    """ Add functionality to *download* command. Perform one or more actions
        that modify the captured images while retaining all of the original
        information (i.e: rotation, metadata annotation)

    """
    def __init__(self, config):
        super(DownloadPlugin, self).__init__(config['download'])

    def download(self, devices, path):
        """ Perform some action after download from devices has finished.

        :param devices: The devices that were downloaded from.
        :type devices: list(DevicePlugin)
        :param path: The destination directory for the downloads
        :type path: unicode

        """
        raise NotImplementedError

    def delete(self, devices):
        """ Perform some action after images have been deleted from the
            devices.

        :param devices: The devices that were downloaded from.
        :type devices: list(DevicePlugin)

        """
        raise NotImplementedError


class FilterPlugin(SpreadsPlugin):
    """ An extension to the *postprocess* command. Performs one or more
        actions that either modify the captured images or generate a
        different output.

    """
    def __init__(self, config):
        super(FilterPlugin, self).__init__(config['postprocess'])

    def process(self, path):
        """ Perform a postprocessing step.

        :param path: The project path
        :type path: unicode

        """
        raise NotImplementedError


def get_devices():
    def all_subclasses(cls):
        """ Get all subclasses and all subclasses of those, for a given class.
            Kudos to http://stackoverflow.com/a/3862957/487903

        """
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in all_subclasses(s)]

    # Import all plugins into spreads namespace
    """ Detect all attached devices and select a fitting driver.

    :returns:  list(DevicePlugin) -- All supported devices that were detected

    """
    candidates = usb.core.find(find_all=True)
    devices = []
    for device in candidates:
        driver = None
        for cls in all_subclasses(DevicePlugin):
            try:
                logging.debug("Matching class %s" % cls)
                if cls.match(device):
                    driver = cls
            except NotImplementedError:
                continue
        if driver:
            devices.append(driver(spreads.config, device))
    if not devices:
        raise Exception("Could not find driver for devices!")
    return devices


def get_plugins(plugin_class):
    """ Get all plugins of a certain type.

    :param plugin_class: The type of plugin to obtain
    :type plugin_class: SpreadsPlugin

    """
    return [x for x in plugin_class.__subclasses__()]

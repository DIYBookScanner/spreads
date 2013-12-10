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
from stevedore.driver import DriverManager
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


    @abc.abstractproperty
    def features(self):
        """ Return device features. """
        return { 'preview': False, }


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
    def prepare_capture(self, path):
        """ Prepare device for scanning.

            What this means exactly is up to the implementation and the type,
            of device, usually it involves things like switching into record
            mode, path and applying all relevant settings.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def capture(self, path):
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

    def prepare_capture(self, devices, path):
        """ Perform some action before capturing begins.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param path: The project path
        :type path: unicode

        """
        pass

    def capture(self, devices, path):
        """ Perform some action after each successful capture.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param path: The project path
        :type path: unicode

        """
        pass

    def finish_capture(self, devices, path):
        """ Perform some action after capturing has finished.

        :param devices: The devices used for capturing
        :type devices: list(DevicePlugin)
        :param path: The project path
        :type path: unicode

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


def get_pluginmanager():
    logger.debug("Creating plugin manager")
    pluginmanager = SpreadsNamedExtensionManager(
        namespace='spreadsplug.hooks',
        names=spreads.config['plugins'].as_str_seq(),
        invoke_on_load=True,
        invoke_args=[spreads.config],
        name_order=True)
    return pluginmanager


def get_driver():
    driver_name = spreads.config["driver"].get(unicode)
    return DriverManager(namespace="spreadsplug.devices",
                         name=driver_name)


def get_devices():
    """ Initialize configured devices.
    """
    driver = get_driver()
    driver_class = driver.driver
    logger.debug("Finding devices for driver \"{0}\"".format(driver))
    usb_devices = filter(lambda dev: driver_class.match(dev),
                         usb.core.find(find_all=True))
    devices = [driver_class(spreads.config['device'], dev) for dev in usb_devices]
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    return devices


def setup_plugin_config():
    pluginmanager = get_pluginmanager()
    driver_name = spreads.config["driver"].get(unicode)
    driver = DriverManager(namespace="spreadsplug.devices",
                           name=driver_name)
    for ext in itertools.chain(pluginmanager, driver):
        logger.debug("Obtaining configuration template for plugin \"{0}\""
                     .format(ext.name))
        tmpl = ext.plugin.configuration_template()
        if ext in driver.extensions:
            section = 'device'
        else:
            section = ext.name
        if not tmpl:
            continue
        # Add default values
        for key, option in tmpl.items():
            # Check if we already have a configuration entry for this setting
            if key in spreads.config[section].keys():
                continue
            logging.info("Adding setting {0} from  plugin {1}"
                            .format(key, ext.name))
            if option.selectable:
                spreads.config[section][key] = option.value[0]
            else:
                spreads.config[section][key] = option.value


def get_relevant_extensions(hooks):
    """ Find all extensions that implement certain hooks.

    :param hooks:   A list of hook method names
    :type hooks:    list(unicode)
    :return:        A generator that yields relevant extensions
    :rtype:         generator(Extension)

    """
    # NOTE: This one is wicked... The goal is to find all extensions that
    #       implement one of the specified hooks.
    #       To do so, we compare the code objects for the appropriate
    #       hook method with the same method in the HookPlugin base class.
    #       If the two are not the same, we can (somewhat) safely assume
    #       that the extension implements this hook and is thus relevant
    #       to us.
    #       Yes, this is not ideal and is due to our somewhat sloppy
    #       plugin interface. That's why...
    # TODO: Refactor plugin interface to make this less painful
    for ext in get_pluginmanager():
        relevant = any(
            getattr(ext.plugin, hook).func_code is not
            getattr(HookPlugin, hook).func_code
            for hook in hooks
        )
        if relevant:
            yield ext

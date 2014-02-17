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

import stevedore
from blinker import Namespace
from stevedore.driver import DriverManager
from stevedore.named import NamedExtensionManager

from spreads.config import OptionTemplate
from spreads.util import abstractclassmethod, DeviceException


logger = logging.getLogger("spreads.plugin")
pluginmanager = None
devices = None


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

    def _load_plugins(self, *args, **kwargs):
        extensions = []
        for ep in self._find_entry_points(self.namespace):
            stevedore.LOG.debug('found extension %r', ep)
            ext = self._load_one_plugin(ep, *args, **kwargs)
            if ext:
                extensions.append(ext)
        return extensions


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
                    value=False, docstring="Temporarily switch target pages"
                                           "(useful for e.g. East-Asian books")
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
        super(DevicePlugin, self).__init__(config['device'])
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


class HookPlugin(SpreadsPlugin):
    """ Base class for HookPlugins.

    Implement one of the available mixin classes to register for the
    appropriate hooks.

    """
    pass


class SubcommandHookMixin(object):
    __metaclass__ = abc.ABCMeta

    @abstractclassmethod
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
    def process(self, path):
        """ Perform one or more actions that either modify the captured images
            or generate a different output.

        .. note:
            This method is intended to operate on the *done* subdfolder of
            the project directory. At the beginning of postprocessing, it
            will contain copies of the images in *raw*. This is to ensure that
            a copy of the original, scanned images will always be available
            for archival purposes.

        :param path:        Project path
        :type path:         pathlib.Path

        """
        pass


class OutputHookMixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def output(self, path):
        """ Assemble an output file from the postprocessed images.

        .. note:
            This method is intended to take its input files from the *done*
            subfolder of the project path and store its output in the
            *out* subfolder.

        :param path:        Project path
        :type path:         pathlib.Path

        """
        pass


def get_pluginmanager(config):
    global pluginmanager
    if pluginmanager is None:
        logger.debug("Creating plugin manager")
        pluginmanager = SpreadsNamedExtensionManager(
            namespace='spreadsplug.hooks',
            names=config['plugins'].as_str_seq(),
            invoke_on_load=True,
            invoke_args=[config],
            name_order=True)
    return pluginmanager


def get_driver(driver_name):
    return DriverManager(namespace="spreadsplug.devices",
                         name=driver_name)


def get_devices(config, force_reload=False):
    """ Initialize configured devices.
    """
    global devices
    if not 'driver' in config.keys():
        raise DeviceException(
            "No driver has been configured\n"
            "Please run `spread configure` to select a driver.")
    if force_reload or not devices:
        driver_manager = get_driver(config["driver"].get())
        driver_class = driver_manager.driver
        logger.debug("Finding devices for driver \"{0}\"".format(driver_manager))
        devices = list(driver_class.yield_devices(config['device']))
        if not devices:
            raise DeviceException("Could not find any compatible devices!")
    return devices


def get_relevant_extensions(plugin_manager, hooks):
    """ Find all extensions that implement certain hooks.

    :param hooks:   HookMixins that are supposed to be implemented
    :type hooks:    list(class)
    :return:        A generator that yields relevant extensions
    :rtype:         generator(Extension)

    """
    for ext in plugin_manager:
        if any(issubclass(ext.plugin, hook) for hook in hooks):
            yield ext

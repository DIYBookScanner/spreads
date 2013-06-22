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

from spreads.util import find_in_path, SpreadsException


class SpreadsPlugin(object):
    """ Plugin base class.

    """
    
    #: The config key to be used for the plugin.  Plugins must set this
    #  attribute or else it will not be found. (type: *unicode*)
    config_key = None

    @classmethod
    def add_arguments(self, parser):
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
            self.config = None


class CameraPlugin(object):
    """ Base class for cameras.

        Subclass to implement support for different cameras. Provides some
        methods that are likely to be of use for CHDK-based cameras.

        .. note::

            Might change a lot in the future, as the API is still tightly
            coupled to CHDK details and should grow more abstract when
            support for more cameras is added.

    """
    @classmethod
    def match(cls, vendor_id, product_id):
        """ Match camera against USB device information.

        :param vendor_id:   idVendor of the USB device
        :type vendor_id:    unicode (hex, zero-padded to 4, e.g. "04a1")
        :param product_id:  idProduct of the USB device
        :type product_id:   unicode (hex, zero-padded to 4, e.g. "12a3")
        :return:            True if the IDs match the implemented model

        """
        raise NotImplementedError

    def __init__(self, config, bus, device):
        """ Set connection information and try to retrieve orientation.

        :param bus:     USB bus number of the camera
        :type bus:      int, str, unicode
        :param device:  USB device number of the camera
        :type bus:      int, str, unicode

        """
        super(BaseCamera, self).__init__(config['camera'])
        self._port = (int(bus), int(device))
        self.orientation = (self._gphoto2(["--get-config",
                                           "/main/settings/ownername"])
                            .split("\n")[-2][9:] or None)

    def _gphoto2(self, args):
        """ Call gphoto2.

        :param args:  The arguments for gphoto2
        :type args:   list
        :returns:     unicode -- combined stdout and stderr of the gphoto2
                                    process.

        """
        cmd = (["gphoto2", "--port", "usb:{0:03},{1:03}".format(*self._port)]
               + args)
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except OSError:
            raise SpreadsException("gphoto2 executable could not be found,"
                                   "please install!")
        return out

    def _ptpcam(self, command):
        """ Call ptpcam to execute command on camera.

        :param command: The CHDK command to execute on the camera
        :type command:  unicode
        :returns:       unicode -- combined stdout and stderr of the ptpcam
                                    process

        """
        bus, device = self._port
        cmd = ["ptpcam", "--dev={0:03}".format(device),
               "--bus={0:03}".format(bus),
               "--chdk='{0}'".format(command)]
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(" ".join(cmd), shell=True,
                                          stderr=subprocess.STDOUT)
        except OSError:
            raise SpreadsException("ptpcam executable could not be found,"
                                   " please install!")
        return out

    def set_orientation(self, orientation):
        """ Set the camera orientation.

        :param orientation: The orientation name
        :type orientation:  unicode in (u"left", u"right")

        """
        self._gphoto2(["--set-config",
                       "/main/settings/ownername={0}".format(orientation)])
        self.orientation = orientation

    def delete_files(self):
        """ Delete all files from camera. """
        raise NotImplementedError

    def download_files(self, path):
        """ Download all files from camera.

        :param path:  The destination path for the downloaded images
        :type path:   unicode

        """
        raise NotImplementedError

    def set_record_mode(self):
        """ Put the camera in record mode. """
        raise NotImplementedError

    def get_zoom(self):
        """ Get current zoom level.

        :returns: int -- the current zoom level

        """
        raise NotImplementedError

    def set_zoom(self, level):
        """ Set zoom level.

        :param level: The zoom level to be used
        :type level:  int

        """
        raise NotImplementedError

    def disable_flash(self):
        """ Disable the camera's flash. """
        raise NotImplementedError

    def set_iso(self, iso_value):
        """ Set the camera's ISO value.

        :param iso_value: The ISO value in ISO/ASA format
        :type iso-value:  int

        """
        raise NotImplementedError

    def disable_ndfilter(self):
        """ Disable the camera's ND Filter. """
        raise NotImplementedError

    def shoot(self, shutter_speed, iso_value):
        """ Shoot a picture.

        :param shutter_speed: The shutter speed to be used
        :type shutter_speed:  float

        """
        raise NotImplementedError

    def play_sound(self, sound_num):
        """ Play sound.

        :param sound_num: The ID of the sound
        :type sound_num:  int

        """
        raise NotImplementedError


class ShootPlugin(SpreadsPlugin):
    """ Add functionality to *shoot* command.

    """
    def __init__(self, config):
        super(ShootPlugin, self).__init__(config['shoot'])

    def snap(self, cameras, count, time):
        """ Perform some action after each successful shot.

        :param cameras: The cameras used for shooting
        :type cameras: list(CameraPlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since shooting began
        :type time: time.timedelta

        """
        raise NotImplementedError

    def finish(self, cameras, count, time):
        """ Perform some action after shooting has finished.

        :param cameras: The cameras used for shooting
        :type cameras: list(CameraPlugin)
        :param count: The shot count
        :type count: int
        :param time: The elapsed time since shooting began
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

    def download(self, cameras, path):
        """ Perform some action after download from cameras has finished.

        :param cameras: The cameras that were downloaded from.
        :type cameras: list(CameraPlugin)
        :param path: The destination directory for the downloads
        :type path: unicode

        """
        raise NotImplementedError

    def delete(self, cameras):
        """ Perform some action after images have been deleted from the
            cameras.

        :param cameras: The cameras that were downloaded from.
        :type cameras: list(CameraPlugin)

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


def get_cameras():
    """ Detect all attached cameras and select a fitting driver.

    :returns:  list(CameraPlugin) -- All supported cameras that were detected

    """
    if not find_in_path('gphoto2'):
        raise Exception("Could not find executable `gphoto2``in $PATH."
                        " Please install the appropriate package(s)!")
    cmd = ['gphoto2', '--auto-detect']
    logging.debug("Running " + " ".join(cmd))
    cam_ports = [re.search(r'usb:\d+,\d+', x).group() for x in
                 subprocess.check_output(cmd).split('\n')[2:-1]]
    cameras = []
    for cam_port in cam_ports:
        bus, device = cam_port[4:].split(',')
        usb_dev = usb.core.find(bus=int(bus), address=int(device))
        vendor_id, product_id = (hex(x)[2:].zfill(4) for x in
                                 (usb_dev.idVendor, usb_dev.idProduct))
        try:
            driver = [x for x in CameraPlugin.__subclasses__()
                      if x.match(vendor_id, product_id)][0]
        except IndexError:
            raise Exception("Could not find driver for camera!")
        cameras.append(driver(bus, device))
    return cameras


def get_plugins(plugin_class):
    """ Get all plugins of a certain type.

    :param plugin_class: The type of plugin to obtain
    :type plugin_class: SpreadsPlugin

    """
    return [x for x in plugin_class.__subclasses__()]

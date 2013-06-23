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

""" Canon A2200 driver
"""
# TODO: Rename to CHDKCameraPlugin?
from __future__ import division, unicode_literals

import logging
import os
import subprocess
import time

from fractions import Fraction
from math import log

from spreads.plugin import CameraPlugin


class CanonA2200CameraPlugin(CameraPlugin):
    ISO_TO_APEX = {
        80: 373,
    }

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--sensitivity', '-S', dest="sensitivity", type=int,
            metavar="<int>", help="ISO sensitivity")
        parser.add_argument(
            "--shutter-speed", '-s', dest="shutter_speed", type=unicode,
            metavar="<int/float/str>", help="Shutter speed")
        parser.add_argument(
            "--zoom-level", "-z", dest="zoom_level", type=int, metavar="<int>",
            help="Zoom level")

    @classmethod
    def match(cls, vendor_id, product_id):
        return vendor_id == "04a9" and product_id == "322a"

    def delete_files(self):
        try:
            self._gphoto2(["--recurse", "-D", "A/store00010001/DCIM/"])
        except subprocess.CalledProcessError:
            # For some reason gphoto2 throws an error despite everything going
            # well...
            pass

    def download_files(self, path):
        cur_dir = os.getcwd()
        os.chdir(path)
        try:
            self._gphoto2(["--recurse", "-P", "A/store00010001/DCIM/"])
        except subprocess.CalledProcessError:
            # For some reason gphoto2 throws an error despite everything going
            # well...
            pass
        os.chdir(cur_dir)

    def prepare_shoot(self):
        self._set_record_mode()
        time.sleep(1)
        self._set_zoom(self.config['zoom_level'].get(int))
        self._set_sensitivity(self.config['sensitivity'].get(int))
        self._disable_flash()
        self._disable_ndfilter()

    def shoot(self):
        """ Shoot a picture. """
        # Set ISO
        self._set_sensitivity(self.config['sensitivity'].get(int))
        # Set shutter speed (has to be set for every shot)
        # Calculate TV96 value from shutter_speed
        shutter_float = (float(Fraction(self.config['shutter_speed']
                         .get(unicode))))
        tv96_value = -96*log(shutter_float)/log(2)
        # Round to nearest multiple of 32
        tv96_value = int(32*round(tv96_value/32))
        self._ptpcam("luar set_tv96_direct({0})".format(tv96_value))
        self._ptpcam("luar shoot()")

    def _set_record_mode(self):
        """ Put the camera in record mode. """
        self._ptpcam("mode 1")

    def _get_zoom(self):
        """ Get current zoom level.

        :returns: int -- the current zoom level

        """
        return int(self._ptpcam('luar get_zoom()').split()[1][-1])

    def _set_zoom(self, level):
        """ Set zoom level.

        :param level: The zoom level to be used
        :type level:  int

        """
        if level > 7:
            raise Exception("Zoom level {0} exceeds the camera's range!"
                            .format(level))
        while self._get_zoom() != level:
            logging.debug(self.orientation, self._get_zoom())
            if self._get_zoom() > level:
                self._ptpcam('luar click("zoom_out")')
            else:
                self._ptpcam('luar click("zoom_in")')
            time.sleep(0.25)

    def _disable_flash(self):
        """ Disable the camera's flash. """
        self._ptpcam("luar set_prop(16, 2)")

    def _set_sensitivity(self, value=80):
        """ Set the camera's ISO value.

        :param iso_value: The ISO value in ISO/ASA format
        :type iso-value:  int

        """
        iso_value = self.config['sensitivity'].get(int)
        try:
            sv96_value = CanonA2200CameraPlugin.ISO_TO_APEX[iso_value]
        except KeyError:
            raise Exception("The desired ISO value is not supported.")
        self._ptpcam("luar set_sv96({0})".format(sv96_value))

    def _disable_ndfilter(self):
        """ Disable the camera's ND Filter. """
        self._ptpcam("luar set_nd_filter(2)")

    def _play_sound(self, sound_num):
        """ Plays one of the following sounds:
                0 = startup sound
                1 = shutter sound
                2 = button press sound
                3 = selftimer
                4 = short beep
                5 = af (auto focus) confirmation
                6 = error beep
        """
        self._ptpcam("lua play_sound({1})".format(sound_num))

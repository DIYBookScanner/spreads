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

from __future__ import division, unicode_literals

import os
import subprocess
import time

from math import log

from spreads.plugin import BaseCamera


class CanonA2200Camera(BaseCamera):
    ISO_TO_APEX = {
        80: 373,
    }

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

    def set_record_mode(self):
        self._ptpcam("mode 1")

    def get_zoom(self):
        return int(self._ptpcam('luar get_zoom()').split()[1][-1])

    def set_zoom(self, level=3):
        if level > 7:
            raise Exception("Zoom level {0} exceeds the camera's range!"
                            .format(level))
        while self.get_zoom() != level:
            if self.get_zoom() > level:
                self._ptpcam('luar click("zoom_out")')
            else:
                self._ptpcam('luar click("zoom_in")')
            time.sleep(0.25)

    def disable_flash(self):
        self._ptpcam("luar set_prop(16, 2)")

    def set_iso(self, iso_value=80):
        try:
            sv96_value = CanonA2200Camera.ISO_TO_APEX[iso_value]
        except KeyError:
            raise Exception("The desired ISO value is not supported.")
        self._ptpcam("luar set_sv96({0})".format(sv96_value))

    def disable_ndfilter(self):
        self._ptpcam("luar set_nd_filter(2)")

    def shoot(self, shutter_speed=1/25, iso_value=80):
        # Set shutter speed (has to be set for every shot)
        self.set_iso(iso_value)
        # Calculate TV96 value from shutter_speed
        tv96_value = -96*log(shutter_speed)/log(2)
        # Round to nearest multiple of 32
        tv96_value = int(32*round(tv96_value/32))
        self._ptpcam("luar set_tv96_direct({0})".format(tv96_value))
        self._ptpcam("luar shoot()")

    def play_sound(self, sound_num):
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

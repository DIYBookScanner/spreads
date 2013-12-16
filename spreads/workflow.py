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

"""
spreads workflow object.
"""

from __future__ import division, unicode_literals

import logging
import os

from concurrent.futures import ThreadPoolExecutor

from spreads.plugin import get_pluginmanager, get_devices
from spreads.util import check_futures_exceptions, DeviceException


class Workflow(object):
    path = None
    _devices = None
    _pluginmanager = None
    _pages_shot = 0

    def __init__(self, config):
        self.logger = logging.getLogger('Workflow')
        self.path = config['path'].get(unicode)
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        self.config = config

    @property
    def plugins(self):
        if self._pluginmanager is None:
            self._pluginmanager = get_pluginmanager(self.config)
        return [ext.obj for ext in self._pluginmanager]

    @property
    def devices(self):
        if self._devices is None:
            self._devices = get_devices(self.config)
        if not self._devices:
            raise DeviceException("Could not find any compatible devices!")
        return self._devices

    def _run_hook(self, hook_name, *args):
        self.logger.debug("Running '{0}' hooks".format(hook_name))
        for plugin in self.plugins:
            getattr(plugin, hook_name)(*args)

    def _get_next_filename(self, extension, target_page=None):
        """ Get next filename that a capture should be stored as.

        If the workflow is shooting with two devices, this will select a
        filename that matches the device's target page (odd/even).

        :param extension: file extension to be used
        :type extension:  str/unicode
        :param target_page: target page of file ('odd/even')
        :type target_page:  str/unicode/None if not applicable
        :return:          absolute path to next filename
                          (e.g. /tmp/proj/003.jpg)
        """
        base_path = os.path.join(self.path, 'raw')
        if not os.path.exists(base_path):
            os.mkdir(base_path)

        if target_page is None:
            return os.path.join(
                base_path, "{03:0}.{1}".format(self._pages_shot, extension))

        next_num = (self._pages_shot+1 if target_page == 'odd'
                    else self._pages_shot)
        return os.path.join(base_path,
                            "{0:03}.{1}".format(next_num, extension))

    def prepare_capture(self):
        self.logger.info("Preparing capture.")
        if any(dev.target_page is None for dev in self.devices):
            raise DeviceException(
                "Target page for at least one of the devicescould not be"
                "determined, please run 'spread configure' to configure your"
                "your devices.")
        with ThreadPoolExecutor(len(self.devices)) as executor:
            futures = []
            self.logger.debug("Preparing capture in devices")
            for dev in self.devices:
                futures.append(executor.submit(dev.prepare_capture, self.path))
        check_futures_exceptions(futures)
        self._run_hook('prepare_capture', self.devices, self.path)

    def capture(self):
        self.logger.info("Triggering capture.")
        if self.config['parallel_capture'].get(bool):
            num_devices = len(self.devices)
        else:
            num_devices = 1

        # TODO: This has to be formalized somewhere, so we can add new file
        #       formats painlessly
        can_shoot_raw = "shoot_raw" in self.config["device"].keys()
        if can_shoot_raw and self.config["device"]["shoot_raw"].get():
            extension = 'dng'
        else:
            extension = 'jpg'

        with ThreadPoolExecutor(num_devices) as executor:
            futures = []
            self.logger.debug("Sending capture command to devices")
            for dev in self.devices:
                img_path = self._get_next_filename(extension, dev.target_page)
                futures.append(executor.submit(dev.capture, img_path))
        check_futures_exceptions(futures)
        self._run_hook('capture', self.devices, self.path)
        self._pages_shot += len(self.devices)

    def finish_capture(self):
        self._run_hook('finish_capture', self.devices, self.path)

    def process(self):
        self.logger.info("Starting postprocessing...")
        self._run_hook('process', self.path)
        self.logger.info("Done with postprocessing!")

    def output(self):
        self.logger.info("Generating output files...")
        out_path = os.path.join(self.path, 'out')
        if not os.path.exists(out_path):
            os.mkdir(out_path)
        self._run_hook('output', self.path)
        self.logger.info("Done generating output files!")

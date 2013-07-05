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
spreads workflow steps.
"""

from __future__ import division, unicode_literals

import logging
import os

from concurrent.futures import ThreadPoolExecutor

from spreads import config
from spreads.plugin import get_pluginmanager


def prepare_capture(devices):
    with ThreadPoolExecutor(len(devices)) as executor:
        for dev in devices:
            executor.submit(dev.prepare_capture)
    for ext in get_pluginmanager():
        ext.obj.prepare_capture(devices)


def capture(devices):
    with ThreadPoolExecutor(len(devices)) as executor:
        for dev in devices:
            executor.submit(dev.capture)
    for ext in get_pluginmanager():
        ext.obj.capture(devices)


def finish_capture(devices):
    for ext in get_pluginmanager():
        ext.obj.finish_capture(devices)


def download(devices, path):
    logging.info("Downloading images from devices to {0}.".format(path))
    keep = config['download']['keep'].get(bool)
    if not os.path.exists(path):
        os.mkdir(path)
    out_paths = [os.path.join(path, x.orientation) for x in devices]
    for subpath in out_paths:
        if not os.path.exists(subpath):
            os.mkdir(subpath)
    with ThreadPoolExecutor(len(devices)) as executor:
        for dev in devices:
            executor.submit(dev.download_files,
                            os.path.join(path, dev.orientation))
    for ext in get_pluginmanager():
        ext.obj.download(devices, path)
    if not keep:
        logging.info("Deleting images from devices")
        with ThreadPoolExecutor(len(devices)) as executor:
            for dev in devices:
                executor.submit(dev.delete_files)
        for ext in get_pluginmanager():
            ext.obj.delete(devices)


def process(path):
    for ext in get_pluginmanager():
        ext.obj.process(path)

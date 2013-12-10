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
from spreads.plugin import get_pluginmanager, DeviceException

logger = logging.getLogger('spreads.workflow')


def prepare_capture(devices, path):
    logger.debug("Preparing capture.")
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    with ThreadPoolExecutor(len(devices)) as executor:
        futures = []
        logger.debug("Preparing capture in devices")
        for dev in devices:
            futures.append(executor.submit(dev.prepare_capture, path))
    if any(x.exception() for x in futures):
        exc = next(x for x in futures if x.exception()).exception()
        raise exc
    for ext in get_pluginmanager():
        logger.debug("Running prepare_capture hooks")
        ext.obj.prepare_capture(devices, path)


def capture(devices, path):
    logger.info("Triggering capture.")
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    if config['parallel_capture'].get(bool):
        num_devices = len(devices)
    else:
        num_devices = 1
    with ThreadPoolExecutor(num_devices) as executor:
        futures = []
        logger.debug("Sending capture command to devices")
        for dev in devices:
            futures.append(executor.submit(dev.capture, path))
    if any(x.exception() for x in futures):
        exc = next(x for x in futures if x.exception()).exception()
        raise exc
    logger.debug("Running capture hooks")
    for ext in get_pluginmanager():
        ext.obj.capture(devices, path)


def finish_capture(devices, path):
    logger.debug("Running finish_capture hooks")
    if not devices:
        raise DeviceException("Could not find any compatible devices!")
    for ext in get_pluginmanager():
        ext.obj.finish_capture(devices, path)


def process(path):
    logger.info("Starting postprocessing...")
    logger.debug("Running process hooks")
    for ext in get_pluginmanager():
        ext.obj.process(path)
    logger.info("Done with postprocessing!")


def output(path):
    logger.info("Generating output files...")
    logger.debug("Running output hooks")
    out_path = os.path.join(path, 'out')
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    for ext in get_pluginmanager():
        ext.obj.output(path)
    logger.info("Done generating output files!")

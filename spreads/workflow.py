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
import sys
import time

from concurrent.futures import ThreadPoolExecutor

from spreads import config
from spreads.plugin import get_pluginmanager

logger = logging.getLogger('spreads.workflow')


def prepare_capture(devices):
    logger.debug("Preparing capture.")
    with ThreadPoolExecutor(len(devices)) as executor:
        futures = []
        logger.debug("Preparing capture in devices")
        for dev in devices:
            futures.append(executor.submit(dev.prepare_capture))
    if any(x.exception() for x in futures):
        exc = next(x for x in futures if x.exception()).exception()
        logger.error("There was an exception while preparing for capture",
                     exc_info=sys.exc_info(exc))
    for ext in get_pluginmanager():
        logger.debug("Running prepare_capture hooks")
        ext.obj.prepare_capture(devices)


def capture(devices):
    logger.info("Triggering capture.")
    with ThreadPoolExecutor(len(devices)) as executor:
        futures = []
        logger.debug("Sending capture command to devices")
        for dev in devices:
            futures.append(executor.submit(dev.capture))
    if any(x.exception() for x in futures):
        exc = next(x for x in futures if x.exception()).exception()
        raise exc
    logger.debug("Running capture hooks")
    for ext in get_pluginmanager():
        ext.obj.capture(devices)


def finish_capture(devices):
    logger.debug("Running finish_capture hooks")
    for ext in get_pluginmanager():
        ext.obj.finish_capture(devices)


def download(devices, path):
    keep = config['download']['keep'].get(bool) or config['keep'].get(bool)
    logger.info("Downloading images from devices to {0}, files will "
                "{1} remain on the devices."
                .format(path, ("not" if not keep else "")))
    if not os.path.exists(path):
        logger.debug("Creating project directory")
        os.mkdir(path)
    out_paths = [os.path.join(path, x.orientation) for x in devices]
    if out_paths:
        logger.debug("Creating camera directories")

    # Flag for when the images are already present
    skip_download = False
    for subpath in out_paths:
        if not os.path.exists(subpath):
            os.mkdir(subpath)
        else:
            logger.info("Images already present, skipping download")
            skip_download = True
    if not skip_download:
        with ThreadPoolExecutor(len(devices)) as executor:
            logger.debug("Starting download process")
            futures = []
            for dev in devices:
                futures.append(executor.submit(
                    dev.download_files,
                    os.path.join(path, dev.orientation))
                )
            if any(x.exception() for x in futures):
                exc = next(x for x in futures if x.exception()).exception()
                raise exc
    logger.debug("Running download hooks")
    for ext in get_pluginmanager():
        ext.obj.download(devices, path)
    # NOTE: Just to be safe...
    time.sleep(5)
    if not keep:
        logger.info("Deleting images from devices")
        with ThreadPoolExecutor(len(devices)) as executor:
            logger.debug("Starting delete process")
            for dev in devices:
                executor.submit(dev.delete_files)
        logger.debug("Running delete hooks")
        for ext in get_pluginmanager():
            ext.obj.delete(devices)


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

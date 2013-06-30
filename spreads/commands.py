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
spreads CLI commands.
"""

from __future__ import division, unicode_literals

import logging
import multiprocessing
import os
import sys
import time

from clint.textui import puts, colored

from spreads import config
from spreads.plugin import get_devices, pluginmanager
from spreads.util import (getch, run_parallel, DeviceException,
                          SpreadsException)


def configure(args=None):
    for orientation in ('left', 'right'):
        puts("Please connect and turn on the device labeled \'{0}\'"
             .format(orientation))
        puts(colored.blue("Press any key when ready."))
        _ = getch()
        devs = get_devices()
        if len(devs) > 1:
            raise DeviceException("Please ensure that only one device is"
                                  " turned on!")
        if not devs:
            raise DeviceException("No device found!")
        devs[0].set_orientation(orientation)
        puts(colored.green("Configured \'{0}\' device.".format(orientation)))
        puts("Please turn off the device.")
        puts(colored.blue("Press any key when ready."))
        _ = getch()


def capture(args=None, devices=[]):
    if not devices:
        puts("Starting capture workflow, please connect and turn on the"
             " devices.")
        puts(colored.blue("Press any key to continue."))
        getch()
        puts("Detecting devices.")
        devices = get_devices()
        if len(devices) != 2:
            raise DeviceException("Please connect and turn on two"
                                  " pre-configured devices! ({0} were"
                                  " found)".format(len(devices)))
        puts(colored.green("Found {0} devices!".format(len(devices))))
        if not any(bool(x.orientation) for x in devices):
            raise DeviceException("At least one of the devices has not been"
                                  " properly configured, please re-run the"
                                  " program with the \'configure\' option!")
    # Set up for capturing
    puts("Setting up devices for capturing.")
    run_parallel([{'func': device.prepare_capture} for device in devices])
    # Start capture loop
    puts(colored.blue("Press 'b' to capture."))
    shot_count = 0
    start_time = time.time()
    pages_per_hour = 0
    capture_keys = config['capture']['capture_keys'].as_str_seq()
    while True:
        if not getch().lower() in capture_keys:
            break
        run_parallel([{'func': x.capture} for x in devices])
        shot_count += len(devices)
        pages_per_hour = (3600/(time.time() - start_time))*shot_count
        status = ("\rShot {0} pages [{1:.0f}/h]"
                  .format(colored.green(unicode(shot_count)), pages_per_hour))
        sys.stdout.write(status)
        sys.stdout.flush()
    sys.stdout.write("\rShot {0} pages in {1:.1f} minutes, average speed was"
                     " {2:.0f} pages per hour"
                     .format(colored.green(str(shot_count)),
                             (time.time() - start_time)/60, pages_per_hour))
    sys.stdout.flush()


def download(args=None, path=None):
    if args.path:
        path = args.path
    if args.keep is not None:
        keep = args.keep
    else:
        keep = config['download']['keep'].get(bool)
    if not os.path.exists(path):
        os.mkdir(path)
    devices = get_devices()
    puts(colored.green("Downloading images from devices"))
    # TODO: Make this more generic, so that devices that capture the whole
    #       spread in one image can be used, too.
    out_paths = [os.path.join(path, x.orientation) for x in devices]
    for subpath in out_paths:
        if not os.path.exists(subpath):
            os.mkdir(subpath)
    run_parallel([{'func': x.download_files,
                   'args': [os.path.join(path, x.orientation)],
                   'kwargs': {}} for x in devices])
    pluginmanager.map(lambda x, y, z: x.obj.download(y, z),
                      devices, path)
    if not keep:
        puts(colored.green("Deleting images from devices"))
        run_parallel([{'func': x.delete_files,
                       'args': [], 'kwargs': {}} for x in devices])
        pluginmanager.map(lambda x, y: x.obj.delete(y),
                          devices)


def postprocess(args=None, path=None):
    if args.path:
        path = args.path
    m_config = config['postprocess']
    num_jobs = m_config['jobs']
    try:
        num_jobs.get(int)
    except:
        m_config['jobs'] = multiprocessing.cpu_count()
    pluginmanager.map(lambda x, y: x.obj.process(y), path)


def wizard(args):
    # TODO: Think about how we can make this more dynamic, i.e. get list of
    #       options for plugin with a description for each entry
    path = args.path
    puts("Please connect and turn on the devices.")
    puts(colored.blue("Press any key to continue."))
    getch()
    puts(colored.green("Detecting devices."))
    devices = get_devices()
    if not any(bool(x.orientation) for x in devices):
        puts(colored.yellow("Devices not yet configured!"))
        puts(colored.blue("Please turn both devices off."
                          " Press any key when ready."))
        while True:
            try:
                configure()
                break
            except DeviceException as e:
                print e

    puts(colored.green("=========================="))
    puts(colored.green("Starting capturing process"))
    puts(colored.green("=========================="))
    capture(devices=devices)

    puts(colored.green("========================="))
    puts(colored.green("Starting download process"))
    puts(colored.green("========================="))
    download(path=path)

    puts(colored.green("======================="))
    puts(colored.green("Starting postprocessing"))
    puts(colored.green("======================="))
    postprocess(path=path)

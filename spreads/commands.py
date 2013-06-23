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

from fractions import Fraction

from clint.textui import puts, colored

from spreads import config
from spreads.plugin import (get_cameras, get_plugins, DownloadPlugin,
                            FilterPlugin)
from spreads.util import (getch, run_parallel, find_in_path, CameraException,
                          SpreadsException)


def configure(args=None):
    for orientation in ('left', 'right'):
        puts("Please connect and turn on the camera labeled \'{0}\'"
             .format(orientation))
        puts(colored.blue("Press any key when ready."))
        _ = getch()
        cams = get_cameras()
        if len(cams) > 1:
            raise CameraException("Please ensure that only one camera is"
                                  " turned on!")
        if not cams:
            raise CameraException("No camera found!")
        cams[0].set_orientation(orientation)
        puts(colored.green("Configured \'{0}\' camera.".format(orientation)))
        puts("Please turn off the camera.")
        puts(colored.blue("Press any key when ready."))
        _ = getch()


def shoot(args=None, cameras=[]):
    if not cameras:
        puts("Starting scanning workflow, please connect and turn on the"
             " cameras.")
        puts(colored.blue("Press any key to continue."))
        getch()
        puts("Detecting cameras.")
        cameras = get_cameras()
        if len(cameras) != 2:
            raise CameraException("Please connect and turn on two"
                                  " pre-configured cameras! ({0} were"
                                  " found)".format(len(cameras)))
        puts(colored.green("Found {0} cameras!".format(len(cameras))))
        if not any(bool(x.orientation) for x in cameras):
            raise CameraException("At least one of the cameras has not been"
                                  " properly configured, please re-run the"
                                  " program with the \'configure\' option!")
    # Set up for shooting
    puts("Setting up cameras for shooting.")
    run_parallel([{'func': camera.prepare_shoot} for camera in cameras])
    # Start shooting loop
    puts(colored.blue("Press 'b' or the footpedal to shoot."))
    shot_count = 0
    start_time = time.time()
    pages_per_hour = 0
    while True:
        if getch() != 'b':
            break
        run_parallel([{'func': x.shoot} for x in cameras])
        shot_count += len(cameras)
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
    plugins = []
    plugin_list = [x for x in config['download']['plugins'].all_contents()]
    plugin_classes = {x.config_key: x for x in get_plugins(DownloadPlugin)}
    for key in plugin_list:
        plugin = plugin_classes[key](config)
        plugins.append(plugin)
    if not os.path.exists(path):
        os.mkdir(path)
    cameras = get_cameras()
    puts(colored.green("Downloading images from cameras"))
    out_paths = [os.path.join(path, x.orientation) for x in cameras]
    for subpath in out_paths:
        if not os.path.exists(subpath):
            os.mkdir(subpath)
    run_parallel([{'func': x.download_files,
                   'args': [os.path.join(path, x.orientation)],
                   'kwargs': {}} for x in cameras])
    for plugin in plugins:
        plugin.download(cameras, path)
    if not keep:
        puts(colored.green("Deleting images from cameras"))
        run_parallel([{'func': x.delete_files,
                       'args': [], 'kwargs': {}} for x in cameras])
        for plugin in plugins:
            plugin.delete(cameras)


def postprocess(args=None, path=None):
    if args.path:
        path = args.path
    m_config = config['postprocess']
    num_jobs = m_config['jobs']
    try:
        num_jobs.get(int)
    except:
        m_config['jobs'] = multiprocessing.cpu_count()
    filter_list = [x for x in m_config['filters'].all_contents()]
    filter_classes = {x.config_key: x for x in get_plugins(FilterPlugin)}
    filters = []
    for key in filter_list:
        filter_ = filter_classes[key](config)
        filter_.process(path)
        filters.append(filter_)


def wizard(args):
    # TODO: Think about how we can make this more dynamic, i.e. get list of
    #       options for plugin with a description for each entry
    path = args.path
    puts("Please connect and turn on the cameras.")
    puts(colored.blue("Press any key to continue."))
    getch()
    puts(colored.green("Detecting cameras."))
    cameras = get_cameras()
    if not any(bool(x.orientation) for x in cameras):
        puts(colored.yellow("Cameras not yet configured!"))
        puts(colored.blue("Please turn both cameras off."
                          " Press any key when ready."))
        while True:
            try:
                configure()
                break
            except CameraException as e:
                print e

    puts(colored.green("========================="))
    puts(colored.green("Starting scanning process"))
    puts(colored.green("========================="))
    shoot(cameras=cameras)

    puts(colored.green("========================="))
    puts(colored.green("Starting download process"))
    puts(colored.green("========================="))
    download(path=path)

    puts(colored.green("======================="))
    puts(colored.green("Starting postprocessing"))
    puts(colored.green("======================="))
    postprocess(path=path)

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
import math
import multiprocessing
import operator
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from fractions import Fraction
from xml.etree.cElementTree import ElementTree as ET

from PIL import Image
from PIL.ExifTags import TAGS
from clint.textui import puts, colored
from spreads.confit import ConfigTypeError

from spreads import config
from spreads.util import (detect_cameras, getch, run_parallel, run_multicore,
                          find_in_path)


def configure():
    for orientation in ('left', 'right'):
        puts("Please connect and turn on the camera labeled \'{0}\'"
             .format(orientation))
        puts(colored.blue("Press any key when ready."))
        _ = getch()
        cams = detect_cameras()
        if len(cams) > 1:
            puts(colored.red("Please ensure that only one camera is"
                             " turned one!"))
            sys.exit(0)
        if not cams:
            puts(colored.red("No camera found!"))
            sys.exit(0)
        cams[0].set_orientation(orientation)
        puts(colored.green("Configured \'{0}\' camera.".format(orientation)))
        puts("Please turn off the camera.")
        puts(colored.blue("Press any key when ready."))
        _ = getch()


def shoot(iso_value=None, shutter_speed=None, zoom_value=None, cameras=[]):
    # TODO: This should *really* be a BaseCamera method
    def setup_camera(camera):
        camera.set_record_mode()
        time.sleep(1)
        camera.set_zoom(zoom_value)
        camera.set_iso(iso_value)
        camera.disable_flash()
        camera.disable_ndfilter()

    if not iso_value:
        iso_value = config['shoot']['sensitivity'].get(int)
    if not shutter_speed:
        shutter_speed = config['shoot']['shutter_speed'].get(unicode)
    if not zoom_value:
        zoom_value = config['shoot']['zoom_level']

    if not find_in_path('ptpcam'):
        raise IOError("Could not find executable `ptpcam``in $PATH."
                      " Please install the appropriate package(s)!")
    if not cameras:
        puts("Starting scanning workflow, please connect and turn on the"
             " cameras.")
        puts(colored.blue("Press any key to continue."))
        getch()
        puts("Detecting cameras.")
        cameras = detect_cameras()
        if len(cameras) != 2:
            puts(colored.red("Please connect and turn on two pre-configured"
                             "cameras! ({0} were found)".format(len(cameras))))
            sys.exit(0)
        puts(colored.green("Found {0} cameras!".format(len(cameras))))
        if not any(bool(x.orientation) for x in cameras):
            puts(colored.red("At least one of the cameras has not been"
                             " properly configured, please re-run the program"
                             " with the \'configure\' option!"))
            sys.exit(0)
    # Set up for shooting
    puts("Setting up cameras for shooting.")
    run_parallel([{'func': setup_camera,
                   'args': [camera]} for camera in cameras])
    # Start shooting loop
    puts(colored.blue("Press 'b' or the footpedal to shoot."))
    shot_count = 0
    start_time = time.time()
    pages_per_hour = 0
    while True:
        if getch() != 'b':
            break
        run_parallel([{'func': x.shoot,
                       'kwargs': {'shutter_speed': float(Fraction(
                                                         shutter_speed)),
                                  'iso_value': iso_value}}
                      for x in cameras])
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


def download(path, keep=None):
    def combine_images(path):
        left_dir = os.path.join(path, 'left')
        right_dir = os.path.join(path, 'right')
        target_dir = os.path.join(path, 'raw')
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        left_pages = [os.path.join(left_dir, x)
                      for x in sorted(os.listdir(left_dir))]
        right_pages = [os.path.join(right_dir, x)
                       for x in sorted(os.listdir(right_dir))]
        if len(left_pages) != len(right_pages):
            puts(colored.yellow("The left and right camera produced an inequal"
                                " amount of images!"))
        combined_pages = reduce(operator.add, zip(right_pages, left_pages))
        puts(colored.green("Combining images."))
        for idx, fname in enumerate(combined_pages):
            fext = os.path.splitext(os.path.split(fname)[1])[1]
            target_file = os.path.join(target_dir, "{0:04d}{1}"
                                       .format(idx, fext))
            shutil.copyfile(fname, target_file)

    if keep is None:
        keep = config['download']['keep'].get(bool)
    if not os.path.exists(path):
        os.mkdir(path)
    cameras = detect_cameras()
    puts(colored.green("Downloading images from cameras"))
    out_paths = [os.path.join(path, x.orientation) for x in cameras]
    for subpath in out_paths:
        if not os.path.exists(subpath):
            os.mkdir(subpath)
    run_parallel([{'func': x.download_files,
                   'args': [os.path.join(path, x.orientation)],
                   'kwargs': {}} for x in cameras])
    if not keep:
        puts(colored.green("Deleting images from cameras"))
        run_parallel([{'func': x.delete_files,
                       'args': [], 'kwargs': {}} for x in cameras])
    combine_images(path)
    shutil.rmtree(os.path.join(path, 'left'))
    shutil.rmtree(os.path.join(path, 'right'))


def postprocess(path, rotate_inverse=False, num_jobs=None, autopilot=None):
    def scantailor_parallel(projectfile, out_dir, num_procs):
        tree = ET(file=projectfile)
        num_files = len(tree.findall('./files/file'))
        files_per_job = int(math.ceil(float(num_files)/num_procs))
        temp_dir = tempfile.mkdtemp(prefix="spreads.")
        splitfiles = []

        for idx in xrange(num_procs):
            tree = ET(file=projectfile)
            root = tree.getroot()
            start = idx*files_per_job
            end = start + files_per_job
            if end > num_files:
                end = None
            for elem in ('files', 'images', 'pages',
                         'file-name-disambiguation'):
                elem_root = root.find(elem)
                to_keep = elem_root.getchildren()[start:end]
                to_remove = [x for x in elem_root.getchildren()
                             if not x in to_keep]
                for node in to_remove:
                    elem_root.remove(node)
            out_file = os.path.join(temp_dir,
                                    "{0}-{1}.ScanTailor".format(
                                    os.path.splitext(os.path.basename(
                                    projectfile))[0], idx))
            tree.write(out_file)
            splitfiles.append(out_file)

        run_multicore(subprocess.call, [[['scantailor-cli', '--start-filter=6',
                                         x, out_dir]] for x in splitfiles],
                      num_procs=num_procs)
        shutil.rmtree(temp_dir)

    def rotate_image(path, left, right, inverse=False):
        logging.debug("Rotating image {0}".format(path))
        im = Image.open(path)
        # Butt-ugly, yes, but works fairly reliably and doesn't require
        # some exotic library not available from PyPi (I'm looking at you,
        # gexiv2...)
        try:
            orientation = re.search(
                'right|left',
                {TAGS.get(tag, tag): value
                 for tag, value in im._getexif().items()}
                ['MakerNote']).group()
            logging.debug("Image {0} has orientation {1}".format(path,
                                                                 orientation))
        except AttributeError:
            # Looks like the images are already rotated and have lost their
            # EXIF information. Or they didn't have any EXIF information
            # to begin with...
            warning = ""
            if im._getexif() is None:
                warning += "No EXIF information. "
            logging.warn(warning + "Cannot determine rotation for image {0}"
                         .format(path))
            return
        if orientation == 'left':
            rotation = left
        else:
            rotation = right
        if inverse:
            rotation *= 2
        logging.debug("Rotating image \'{0}\' by {1} degrees"
                      .format(path, rotation))
        im.rotate(rotation).save(path)

    def assemble_pdf(img_path, output):
        logging.info("Assembling PDF.")
        img_files = [os.path.join(img_path, x)
                     for x in os.listdir(img_path)
                     if x.lower().endswith('tif')]
        cmd = ["pdfbeads"] + img_files + ["-o", output]
        logging.debug("Running " + " ".join(cmd))
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def assemble_djvu(img_path, output):
        logging.info("Assembling DJVU.")
        orig_dir = os.path.abspath(os.curdir)
        os.chdir(os.path.join(img_path, '..'))
        cmd = ["djvubind", img_path]
        if config['postprocess']['djvu']['ocr'].get(unicode) == 'none':
            cmd.append("--no-ocr")
        logging.debug("Running " + " ".join(cmd))
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        os.rename("book.djvu", "{0}.djvu".format(
                  os.path.basename(os.path.abspath(os.curdir))))
        os.chdir(orig_dir)

    m_config = config['postprocess']
    if not num_jobs:
        try:
            num_jobs = m_config['jobs'].get(int)
        except:
            num_jobs = multiprocessing.cpu_count()
    if autopilot is None:
        autopilot = m_config['autopilot']
    if not find_in_path('scantailor-cli'):
        raise Exception("Could not find executable `scantailor-cli` in $PATH."
                        "Please install the appropriate package(s)!")
    if not autopilot and not find_in_path('scantailor'):
        raise Exception("Could not find executable `scantailor` in $PATH."
                        "Please install the appropriate package(s)!")
    if not find_in_path('pdfbeads'):
        raise Exception("Could not find executable `pdfbeads` in $PATH."
                        "Please install the appropriate package(s)!")
    img_dir = os.path.join(path, 'raw')
    # Rotation, left -> cw; right -> ccw
    puts(colored.green("Rotating images"))
    rotate_config = m_config['rotation']
    run_multicore(rotate_image, [[os.path.join(img_dir, x)]
                                 for x in os.listdir(img_dir)],
                  {'inverse': rotate_inverse,
                   'left': rotate_config['left'].get(int),
                   'right': rotate_config['right'].get(int)},
                  num_procs=num_jobs)

    # TODO: Calculate DPI from grid and set it in the JPGs
    # TODO: Dewarp the pictures from grid information

    # Generate ScanTailor configuration
    projectfile = os.path.join(path, "{0}.ScanTailor".format(
        os.path.basename(path)))
    out_dir = os.path.join(path, 'done')
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    puts(colored.green("Generating ScanTailor configuration"))
    st_config = m_config['scantailor']
    filterconf = [st_config[x].get(bool)
                  for x in ('rotate', 'split_pages', 'deskew', 'content',
                            'auto_margins')]
    start_filter = filterconf.index(True)+1
    end_filter = len(filterconf) - list(reversed(filterconf)).index(True)+1
    generation_cmd = ['scantailor-cli',
                      '--start-filter={0}'.format(start_filter),
                      '--end-filter={0}'.format(end_filter),
                      '--layout=1.5',
                      '--margins-top={0}'.format(st_config['margins'][0]),
                      '--margins-right={0}'.format(st_config['margins'][1]),
                      '--margins-bottom={0}'.format(st_config['margins'][2]),
                      '--margins-left={0}'.format(st_config['margins'][3]),
                      '-o={0}'.format(projectfile), img_dir, out_dir]
    logging.debug(" ".join(generation_cmd))
    subprocess.call(generation_cmd)
    if not autopilot:
        puts(colored.green("Opening ScanTailor GUI for manual adjustment"))
        subprocess.call(['scantailor', projectfile])
    puts(colored.green("Generating output images from ScanTailor"
                       " configuration."))
    scantailor_parallel(projectfile, out_dir, num_procs=num_jobs)
    puts(colored.green("Generating PDF"))
    pdf_file = os.path.join(path, "{0}.pdf".format(os.path.basename(path)))
    djvu_file = os.path.join(path, "{0}.djvu".format(os.path.basename(path)))
    assemble_pdf(out_dir, pdf_file)
    assemble_djvu(out_dir, djvu_file)


def wizard(path):
    puts("Please connect and turn on the cameras.")
    puts(colored.blue("Press any key to continue."))
    getch()
    puts(colored.green("Detecting cameras."))
    cameras = detect_cameras()
    if not any(bool(x.orientation) for x in cameras):
        puts(colored.yellow("Cameras not yet configured!"))
        puts(colored.blue("Please turn both cameras off."
                          " Press any key when ready."))
        configure()

    puts(colored.green("========================="))
    puts(colored.green("Starting scanning process"))
    puts(colored.green("========================="))
    iso_value = raw_input("ISO [80]: ")
    if not iso_value:
        iso_value = 80
    else:
        iso_value = int(iso_value)
    shutter_speed = raw_input("Shutter speed [1/25]: ")
    if not shutter_speed:
        shutter_speed = 0.04
    else:
        shutter_speed = float(Fraction(shutter_speed))
    zoom_value = raw_input("Zoom value [3]: ")
    if not zoom_value:
        zoom_value = 3
    else:
        zoom_value = int(zoom_value)
    shoot(iso_value=iso_value, shutter_speed=shutter_speed,
          zoom_value=zoom_value, cameras=cameras)

    puts(colored.green("========================="))
    puts(colored.green("Starting download process"))
    puts(colored.green("========================="))
    keep = raw_input("Keep images on camera? [n]").lower() == 'y'
    download(path=path, keep=keep)

    puts(colored.green("======================="))
    puts(colored.green("Starting postprocessing"))
    puts(colored.green("======================="))
    rotate_inverse = (raw_input("Inverse rotation? (+/-180°) [n]")
                      .lower() == 'y')
    num_jobs = raw_input("Number of concurrent jobs? [auto]")
    if not num_jobs:
        num_jobs = None
    else:
        num_jobs = int(num_jobs)
    autopilot = (raw_input("Do you want to manually adjust the generated"
                           " ScanTailor configuration? [y]: ").lower() == 'n')
    postprocess(path, rotate_inverse=rotate_inverse, num_jobs=num_jobs,
                autopilot=autopilot)

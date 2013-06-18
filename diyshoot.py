#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
Tool to facilitate book digitization with the DIY BookScanner.

Copyright (c) 2013 Johannes Baiter. All rights reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import argparse
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
from xml.etree.cElementTree import ElementTree as ET

from clint.textui import puts, colored
from PIL import Image
from PIL.ExifTags import TAGS


# Kudos to http://stackoverflow.com/a/1394994/487903
try:
    from msvcrt import getch
except ImportError:
    def getch():
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


class Camera(object):
    def __init__(self, usb_port):
        self._port = usb_port
        self.orientation = (self._gphoto2(["--get-config",
                                           "/main/settings/ownername"])
                            .split("\n")[-2][9:] or None)

    def _gphoto2(self, args):
        cmd = (["gphoto2", "--port", self._port] + args)
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except OSError:
            logging.error("gphoto2 executable could not be found, please"
                          "install!")
            sys.exit(0)
        return out

    def _ptpcam(self, command):
        bus, device = self._port[4:].split(',')
        cmd = ["/usr/bin/ptpcam", "--dev={0}".format(device),
               "--bus={0}".format(bus),
               "--chdk='{0}'".format(command)]
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(" ".join(cmd), shell=True,
                                          stderr=subprocess.STDOUT)
        except OSError:
            logging.error("ptpcam executable could not be found, please"
                          "install!")
            sys.exit(0)
        return out

    def set_orientation(self, orientation):
        self._gphoto2(["--set-config",
                       "/main/settings/ownername={0}".format(orientation)])
        self.orientation = orientation

    def delete_files(self):
        try:
            self._gphoto2(["--recurse", "-D", "A/store00010001/DCIM/"])
        except subprocess.CalledProcessError:
            # For some reason gphoto2 throws an error despite everything going
            # well...
            pass

    def download_files(self, path):
        cur_dir = os.getcwd()
        if not os.path.exists(path):
            os.mkdir(path)
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
        while self.get_zoom() != level:
            if self.get_zoom() > level:
                self._ptpcam('luar click("zoom_out")')
            else:
                self._ptpcam('luar click("zoom_in")')
            time.sleep(0.25)

    def disable_flash(self):
        self._ptpcam("luar set_prop(16, 2)")

    def set_iso(self, iso_value=373):
        self._ptpcam("luar set_sv96({0})".format(iso_value))

    def disable_ndfilter(self):
        self._ptpcam("luar set_nd_filter(2)")

    def shoot(self, shutter_speed=320, iso_value=373):
        """ Values for shutter speed are as follows:
            http://chdk.wikia.com/wiki/CHDK_scripting#set_tv96_direct
        """
        # Set shutter speed (has to be set for every shot)
        self._ptpcam("luar set_sv96({0})".format(iso_value))
        self._ptpcam("luar set_tv96_direct({0})".format(shutter_speed))
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


def _run_parallel(jobs, num_procs=None):
    class Worker(multiprocessing.Process):
        def __init__(self, queue):
            super(Worker, self).__init__()
            self.queue = queue

        def run(self):
            for job in iter(self.queue.get, None):
                job['func'](*job['args'], **job['kwargs'])

    if not num_procs:
        num_procs = multiprocessing.cpu_count()
    running = []
    queue = multiprocessing.Queue()
    for i in xrange(num_procs):
        w = Worker(queue)
        running.append(w)
        w.start()
    for job in jobs:
        queue.put(job)
    for i in xrange(num_procs):
        queue.put(None)
    for worker in running:
        worker.join()


def _detect_cameras():
    cmd = ['gphoto2', '--auto-detect']
    logging.debug("Running " + " ".join(cmd))
    cams = [Camera(re.search(r'usb:\d+,\d+', x).group()) for x in
            subprocess.check_output(cmd).split('\n')[2:-1]]
    return cams


def _combine_images(path):
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
        target_file = os.path.join(target_dir, "{0:04d}{1}".format(idx, fext))
        shutil.copyfile(fname, target_file)


def _rotate_image(path, inverse=False):
    logging.debug("Rotating image {0}".format(path))
    im = Image.open(path)
    # Butt-ugly, yes, but works fairly reliably and doesn't require
    # some exotic library not available from PyPi (I'm looking at you,
    # gexiv2...)
    orientation = re.search(
        'right|left',
        {TAGS.get(tag, tag): value for tag, value in im._getexif().items()}
        ['MakerNote']).group()
    logging.debug("Image {0} has orientation {1}".format(path, orientation))
    rotation = 90
    if inverse:
        rotation *= 2
    if orientation == 'left':
        rotation *= -1
    logging.debug("Rotating image \'{0}\' by {1} degrees"
                  .format(path, rotation))
    im.rotate(rotation).save(path)


def _scantailor_parallel(projectfile, out_dir, num_procs=None):
    if not num_procs:
        num_procs = multiprocessing.cpu_count()
    tree = ET(file=projectfile)
    num_files = len(tree.findall('./files/file'))
    files_per_job = int(math.ceil(float(num_files)/num_procs))
    temp_dir = tempfile.mkdtemp(prefix="diyshoot")
    splitfiles = []

    for idx in xrange(num_procs):
        tree = ET(file=projectfile)
        root = tree.getroot()
        start = idx*files_per_job
        end = start + files_per_job
        if end > num_files:
            end = None
        for elem in ('files', 'images', 'pages', 'file-name-disambiguation'):
            elem_root = root.find(elem)
            to_keep = elem_root.getchildren()[start:end]
            to_remove = [x for x in elem_root.getchildren()
                         if not x in to_keep]
            for node in to_remove:
                elem_root.remove(node)
        out_file = os.path.join(temp_dir,
                                "{0}-{1}.ScanTailor".format(
                                os.path.splitext(os.path.basename(projectfile))
                                [0], idx))
        tree.write(out_file)
        splitfiles.append(out_file)

    _run_parallel([{'func': subprocess.call, 'args': [['scantailor-cli',
                                                      '--start-filter=6',
                                                      x, out_dir]],
                    'kwargs': {}} for x in splitfiles], num_procs=num_procs)
    shutil.rmtree(temp_dir)


def configure():
    for orientation in ('left', 'right'):
        puts("Please connect the camera labeled \'{0}\'".format(orientation))
        puts(colored.blue("Press any key when ready."))
        cams = _detect_cameras()
        if len(cams) > 1:
            puts(colored.red("Please ensure that only one camera is"
                             "connected!"))
            sys.exit(0)
        if not cams:
            puts(colored.red("No camera found!"))
            sys.exit(0)
        cams[0].set_orientation(orientation)
        puts(colored.green("Configured \'{0}\' camera.".format(orientation)))


def shoot(iso_value=373, shutter_speed=448, zoom_value=3, cameras=[]):
    if not cameras:
        puts("Starting scanning workflow, please connect the cameras.")
        puts(colored.blue("Press any key to continue."))
        getch()
        puts("Detecting cameras.")
        cameras = _detect_cameras()
        if len(cameras) != 2:
            puts(colored.red("Please connect two pre-configured cameras!"
                            " ({0} were found)".format(len(cameras))))
            sys.exit(0)
        puts(colored.green("Found {0} cameras!".format(len(cameras))))
        if not any(bool(x.orientation) for x in cameras):
            puts(colored.red("At least one of the cameras has not been properly"
                            "configured, please re-run the program with the"
                            "\'configure\' option!"))
            sys.exit(0)
    # Set up for shooting
    for camera in cameras:
        puts("Setting up {0} camera.".format(camera.orientation))
        camera.set_record_mode()
        time.sleep(1)
        camera.set_zoom(zoom_value)
        camera.set_iso(iso_value)
        camera.disable_flash()
        camera.disable_ndfilter()
    # Start shooting loop
    puts(colored.blue("Press 'b' or the footpedal to shoot."))
    shot_count = 0
    start_time = time.time()
    while True:
        if getch() != 'b':
            break
        _run_parallel([{'func': x.shoot, 'args': [],
                        'kwargs': {'shutter_speed': shutter_speed,
                                   'iso_value': iso_value}}
                       for x in cameras])
        shot_count += len(cameras)
        pages_per_hour = (3600/(time.time() - start_time))*shot_count
        status = "\r{0} pages [{0:.0f}/h]".format(colored.blue(shot_count),
                                                  pages_per_hour)
        sys.stdout.write(status)
        sys.stdout.flush()


def download(path, keep=False):
    if not os.path.exists(path):
        os.mkdir(path)
    cameras = _detect_cameras()
    puts(colored.green("Downloading images from cameras"))
    _run_parallel([{'func': x.download_files,
                    'args': [os.path.join(path, x.orientation)],
                    'kwargs': {}} for x in cameras])
    if not args.keep:
        puts(colored.green("Deleting images from cameras"))
        _run_parallel([{'func': x.delete_files, 'args': [], 'kwargs': {}}
                       for x in cameras])
    _combine_images(path)
    shutil.rmtree(os.path.join(path, 'left'))
    shutil.rmtree(os.path.join(path, 'right'))


def postprocess(path, rotate_inverse=False, num_jobs=None, autopilot=False):
    img_dir = os.path.join(path, 'raw')
    # Rotation, left -> cw; right -> ccw
    puts(colored.green("Rotating images"))
    _run_parallel([{'func': _rotate_image, 'args': [os.path.join(img_dir, x)],
                    'kwargs': {'inverse': rotate_inverse}}
                   for x in os.listdir(img_dir)], num_procs=num_jobs)

    # TODO: Calculate DPI from grid and set it in the JPGs
    # TODO: Dewarp the pictures from grid information

    # Generate ScanTailor configuration
    projectfile = os.path.join(path, "{0}.ScanTailor".format(
        os.path.basename(path)))
    out_dir = os.path.join(path, 'done')
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    puts(colored.green("Generating ScanTailor configuration"))
    generation_cmd = ['scantailor-cli', '--start-filter=2', '--end-filter=5',
                      '--layout=1.5', '--margins=2.5',
                      '-o={0}'.format(projectfile), img_dir, out_dir]
    logging.debug(" ".join(generation_cmd))
    subprocess.call(generation_cmd)
    if not autopilot:
        puts(colored.green("Opening ScanTailor GUI for manual adjustment"))
        subprocess.call(['scantailor', projectfile])
    puts(colored.green("Generating output images from ScanTailor"
                       " configuration."))
    _scantailor_parallel(projectfile, out_dir, num_procs=num_jobs)


def wizard(path):
    puts("Please connect the cameras.")
    puts(colored.blue("Press any key to continue."))
    getch()
    puts(colored.green("Detecting cameras."))
    cameras = _detect_cameras()
    if not any(bool(x.orientation) for x in cameras):
        puts(colored.yellow("Cameras not yet configured!"))
        puts(colored.blue("Please disconnect both cameras."
                          " Press any key when ready."))
        configure()

    puts(colored.green("========================="))
    puts(colored.green("Starting scanning process"))
    puts(colored.green("========================="))
    iso_value = raw_input("ISO [373]: ")
    if not iso_value:
        iso_value = 373
    else:
        iso_value = int(iso_value)
    shutter_speed = raw_input("Shutter speed [448]: ")
    if not shutter_speed:
        shutter_speed = 448
    else:
        shutter_speed = int(shutter_speed)
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
    postprocessing(path, rotate_inverse=rotate_inverse, num_jobs=num_jobs,
                   autopilot=autopilot)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scanning Tool for  DIY Book Scanner")
    parser.add_argument(
        '--verbose', '-v', dest="verbose", action="store_true")
    subparsers = parser.add_subparsers()

    wizard_parser = subparsers.add_parser(
        'wizard', help="Interactive mode")
    wizard_parser.add_argument(
        "path", help="Path where scanned images are to be stored")
    wizard_parser.set_defaults(func=wizard)

    config_parser = subparsers.add_parser(
        'configure', help="Perform initial configuration of the cameras.")
    config_parser.set_defaults(func=configure)

    shoot_parser = subparsers.add_parser(
        'shoot', help="Start the shooting workflow")
    shoot_parser.add_argument(
        '--iso', '-i', dest="iso_value", type=int, default=373,
        metavar="<int>", help="ISO value (APEX96)")
    shoot_parser.add_argument(
        "--shutter", '-s', dest="shutter_speed", type=int, default=448,
        metavar="<int>", help="Shutter speed value (APEX96). For more"
        " information, visit http://chdk.wikia.com/wiki/CHDK_scripting"
        "#set_tv96_direct")
    shoot_parser.add_argument(
        "--zoom", "-z", dest="zoom_value", type=int, metavar="<int>",
        default=3, help="Zoom level")
    shoot_parser.set_defaults(func=shoot)

    download_parser = subparsers.add_parser(
        'download', help="Download scanned images.")
    download_parser.add_argument(
        "path", help="Path where scanned images are to be stored")
    download_parser.add_argument(
        "--keep", "-k", dest="keep", action="store_true",
        help="Keep files on cameras after download")
    download_parser.set_defaults(func=download)

    postprocess_parser = subparsers.add_parser(
        'postprocess',
        help="Postprocess scanned images.")
    postprocess_parser.add_argument(
        "path", help="Path where scanned images are stored")
    postprocess_parser.add_argument(
        "--rotate-inverse", "-ri", dest="rotate_inverse", action="store_true",
        help="Rotate by +/- 180° instead of +/- 90°")
    postprocess_parser.add_argument(
        "--jobs", "-j", dest="num_jobs", type=int, default=None,
        metavar="<int>", help="Number of concurrent processes")
    postprocess_parser.add_argument(
        "--auto", "-a", dest="autopilot", action="store_true",
        help="Don't prompt user to edit ScanTailor configuration")
    postprocess_parser.set_defaults(func=postprocess)

    args = parser.parse_args()
    loglevel = logging.INFO
    if args.verbose:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    func_args = dict(x for x in args._get_kwargs()
                     if x[0] not in ('func', 'verbose'))
    logging.debug(func_args)
    args.func(**func_args)

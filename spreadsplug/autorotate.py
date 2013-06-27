# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import os
import re

from PIL import Image
from PIL.ExifTags import TAGS

from spreads.plugin import HookPlugin
from spreads.util import run_multicore


class AutoRotatePlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == 'postprocess':
            parser.add_argument("--rotate-inverse", "-ri",
                                dest="rotate_inverse", action="store_true",
                                help="Rotate by +/- 180° instead of +/- 90°")

    def __init__(self, config):
        self.config = config['postprocess']

    def rotate_image(self, path, left, right, inverse=False):
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

    def process(self, path):
        logging.info("Rotating images")
        # FIXME: Get this from commandline arguments
        img_dir = os.path.join(path, 'raw')
        num_jobs = self.parent_config['jobs'].get(int)
        run_multicore(self.rotate_image, [[os.path.join(img_dir, x)]
                                           for x in os.listdir(img_dir)],
                      {'inverse': (self.config['autorotate']['rotate_inverse']
                                   .get(bool)),
                       'left': self.config['autorotate']['left'].get(int),
                       'right': self.config['autorotate']['right'].get(int)},
                      num_procs=num_jobs)

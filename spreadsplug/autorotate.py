# -*- coding: utf-8 -*-

from __future__ import division

import logging
import os

import wand.image

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
        # Read the JPEG comment that contains the orientation of the image
        with open(path, 'rb') as fp:
            fp.seek(-12, 2)
            data = fp.read()
            orientation = data[data.find('\xfe')+1:].lower()
            logging.debug(orientation)
        if orientation not in ('left', 'right'):
            logging.warn("Cannot determine rotation for image {0}!"
                         .format(path))
            return
        logging.debug("Orientation for \"{0}\" is {1}"
                      .format(path, orientation))

        with wand.image.Image(filename=path) as img:
            if orientation == 'left':
                rotation = left
            else:
                rotation = right
            if inverse:
                rotation *= 2
            logging.debug("Rotating image \'{0}\' by {1} degrees"
                          .format(path, rotation))
            img.rotate(rotation)
            img.save(filename=path)

    def process(self, path):
        logging.info("Rotating images")
        img_dir = os.path.join(path, 'raw')
        num_jobs = self.config['jobs'].get(int)
        run_multicore(self.rotate_image, [[os.path.join(img_dir, x)]
                                          for x in os.listdir(img_dir)],
                      {'inverse': (self.config['autorotate']['rotate_inverse']
                                   .get(bool)),
                       'left': self.config['autorotate']['left'].get(int),
                       'right': self.config['autorotate']['right'].get(int)},
                      num_procs=num_jobs)

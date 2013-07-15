# -*- coding: utf-8 -*-

from __future__ import division

import logging
import os

import pexif
import wand.image
from concurrent import futures

from spreads.plugin import HookPlugin

logger = logging.getLogger('spreadsplug.autorotate')


def rotate_image(path, left, right, inverse=False):
    # Silence Wand logger
    (logging.getLogger("wand")
            .setLevel(logging.ERROR))
    logger.debug("Rotating image {0}".format(path))
    # Read the JPEG comment that contains the orientation of the image
    img = pexif.JpegFile.fromFile(path)
    try:
        if img.exif.primary.Orientation == [8]:
            rotation = left
        elif img.exif.primary.Orientation == [6]:
            rotation = right
        else:
            raise Exception("Invalid value for orientation: {0}"
                            .format(img.exif.primary.Orientation))
    except:
        logger.warn("Cannot determine rotation for image {0}!"
                    .format(path))
        return
    if inverse:
                rotation *= 2
    logger.debug("Orientation for \"{0}\" is {1}"
                 .format(path, orientation))
    with wand.image.Image(filename=path) as img:
        logger.debug("Rotating image \'{0}\' by {1} degrees"
                     .format(path, rotation))
        img.rotate(rotation)
        img.save(filename=path)


class AutoRotatePlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == 'postprocess':
            parser.add_argument("--rotate-inverse", "-ri",
                                dest="rotate_inverse", action="store_true",
                                help="Rotate by +/- 180° instead of +/- 90°")

    def __init__(self, config):
        self.config = config['postprocess']

    def process(self, path):
        img_dir = os.path.join(path, 'raw')
        logger.info("Rotating images in {0}".format(img_dir))
        #num_jobs = self.config['jobs'].get(int)
        #logger.debug("Using {0} cores".format(num_jobs))
        logger.debug("Spawning the processes...")
        with futures.ProcessPoolExecutor() as executor:
            for img in os.listdir(img_dir):
                executor.submit(
                    rotate_image,
                    os.path.join(img_dir, img),
                    inverse=(self.config['autorotate']['rotate_inverse']
                             .get(bool)),
                    left=self.config['autorotate']['left'].get(int),
                    right=self.config['autorotate']['right'].get(int),
                )

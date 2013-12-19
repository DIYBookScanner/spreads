# -*- coding: utf-8 -*-

from __future__ import division

import logging
import os

import wand.image
from concurrent import futures
from pexif import JpegFile

from spreads.plugin import HookPlugin, PluginOption

logger = logging.getLogger('spreadsplug.autorotate')


def rotate_image(path, rotation):
    with wand.image.Image(filename=path) as img:
        logger.debug("Rotating image \'{0}\' by {1} degrees"
                     .format(path, rotation))
        if img.height > img.width:
            logger.info("Image already rotated, skipping...")
        else:
            img.rotate(rotation)
            img.save(filename=path)
    # Update EXIF orientation
    img = JpegFile.fromFile(path)
    if not img.exif.primary.Orientation == [1]:
        logger.debug("Updating EXIF information for image '{0}'".format(path))
        img.exif.primary.Orientation = [1]
        img.writeFile(path)


class AutoRotatePlugin(HookPlugin):
    __name__ = 'autorotate'

    @classmethod
    def configuration_template(cls):
        conf = {'rotate_odd': PluginOption(-90, "Rotation applied to odd pages"),
                'rotate_even': PluginOption(90, "Rotation applied to even pages"),
                }
        return conf

    def process(self, path):
        img_dir = os.path.join(path, 'raw')
        # Silence Wand logger
        (logging.getLogger("wand")
                .setLevel(logging.ERROR))
        logger.info("Rotating images in {0}".format(img_dir))
        with futures.ProcessPoolExecutor() as executor:
            for imgpath in os.listdir(img_dir):
                try:
                    img = JpegFile.fromFile(os.path.join(img_dir, imgpath))
                    if img.exif.primary.Orientation == [8]:
                        rotation = self.config['rotate_odd'].get(int)
                    elif img.exif.primary.Orientation == [6]:
                        rotation = self.config['rotate_even'].get(int)
                    elif img.exif.primary.Orientation == [1]:
                        # Already rotated, so we skip it
                        continue
                    else:
                        raise Exception("Invalid value for orientation: {0}"
                                        .format(img.exif.primary.Orientation))
                except Exception as exc:
                    logger.warn("Cannot determine rotation for image {0}!"
                                .format(imgpath))
                    logger.exception(exc)
                    continue
                logger.debug("Orientation for \"{0}\" is {1}"
                             .format(imgpath, rotation))
                executor.submit(
                    rotate_image,
                    os.path.join(img_dir, imgpath),
                    rotation=rotation
                )

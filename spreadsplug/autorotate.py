# -*- coding: utf-8 -*-

import logging
import subprocess

from concurrent import futures
from jpegtran import JPEGImage

from spreads.plugin import HookPlugin, PluginOption
from spreads.util import find_in_path, MissingDependencyException

logger = logging.getLogger('spreadsplug.autorotate')

def autorotate_image(path):
    img = JPEGImage(path)
    if img.exif_orientation is None:
        logger.warn("Image {0} did not have any EXIF rotation, did not rotate."
                    .format(path))
        return
    elif img.exif_orientation == 1:
        logger.info("Image {0} is already rotated.".format(path))
        return
    rotated = img.exif_autotransform()
    img.save(path)


class AutoRotatePlugin(HookPlugin):
    __name__ = 'autorotate'

    def process(self, path):
        img_dir = path / 'raw'
        logger.info("Rotating images in {0}".format(img_dir))
        with futures.ProcessPoolExecutor() as executor:
            for imgpath in sorted(img_dir.iterdir()):
                executor.submit(autorotate_image, imgpath)

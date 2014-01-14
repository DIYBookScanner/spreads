# -*- coding: utf-8 -*-

import logging
import subprocess

import wand.image
from concurrent import futures

from spreads.plugin import HookPlugin, PluginOption
from spreads.util import find_in_path, MissingDependencyException

logger = logging.getLogger('spreadsplug.autorotate')

try:
    import pyexiv2

    def get_exif_orientation(image, orientation):
        metadata = pyexiv2.ImageMetadata(image)
        metadata.read()
        return int(metadata['Image.Exif.Orientation'].value)

except ImportError:
    if not find_in_path('exiftool'):
        raise MissingDependencyException("Could not find executable `exiftool`"
                                         " in $PATH. Please install the"
                                         " appropriate package(s)!")

    def get_exif_orientation(image, orientation):
        return int(subprocess.check_output(
            ['exiftool', '-Orientation', '-n',
             unicode(image)]).split(":")[1].strip())


def rotate_image(path, rotation):
    with wand.image.Image(filename=unicode(path)) as img:
        logger.debug("Rotating image \'{0}\' by {1} degrees"
                     .format(path, rotation))
        if img.height > img.width:
            logger.info("Image already rotated, skipping...")
        else:
            img.rotate(rotation)
            img.save(filename=unicode(path))
    # Update EXIF orientation
    if not get_exif_orientation(path) == 1:
        logger.debug("Updating EXIF information for image '{0}'".format(path))
        subprocess.check_output(['exiftool', '-Orientation=1', '-n',
                                 '-overwrite_original', unicode(path)])


class AutoRotatePlugin(HookPlugin):
    __name__ = 'autorotate'

    @classmethod
    def configuration_template(cls):
        conf = {'rotate_odd': PluginOption(-90,
                                           "Rotation applied to odd pages"),
                'rotate_even': PluginOption(90,
                                            "Rotation applied to even pages"),
                }
        return conf

    def process(self, path):
        img_dir = path / 'raw'
        # Silence Wand logger
        (logging.getLogger("wand")
                .setLevel(logging.ERROR))
        logger.info("Rotating images in {0}".format(img_dir))
        with futures.ProcessPoolExecutor() as executor:
            for imgpath in sorted(img_dir.iterdir()):
                try:
                    exif_orientation = get_exif_orientation(imgpath)
                    if exif_orientation == 8:
                        rotation = self.config['rotate_odd'].get(int)
                    elif exif_orientation == 6:
                        rotation = self.config['rotate_even'].get(int)
                    elif exif_orientation == 1:
                        # Already rotated, so we skip it
                        continue
                    else:
                        raise Exception("Invalid value for orientation: {0}"
                                        .format(exif_orientation))
                except Exception as exc:
                    logger.warn("Cannot determine rotation for image {0}!"
                                .format(imgpath))
                    logger.exception(exc)
                    continue
                logger.debug("Orientation for \"{0}\" is {1}"
                             .format(imgpath, rotation))
                executor.submit(rotate_image, imgpath, rotation=rotation)

import logging
import os
import re

from PIL import Image
from PIL.ExifTags import TAGS

from spreads.plugin import FilterPlugin
from spreads.util import run_multicore


class AutoRotateFilter(FilterPlugin):
    config_key = 'autorotate'

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
        rotate_inverse = False
        img_dir = os.path.join(path, 'raw')
        num_jobs = self.parent_config['jobs'].get(int)
        run_multicore(self.rotate_image, [[os.path.join(img_dir, x)]
                                           for x in os.listdir(img_dir)],
                      {'inverse': rotate_inverse,
                       'left': self.config['left'].get(int),
                       'right': self.config['right'].get(int)},
                      num_procs=num_jobs)

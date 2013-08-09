import logging
import operator
import os

import wand.api
import wand.image
from concurrent import futures

from spreads.plugin import HookPlugin

logger = logging.getLogger('spreadsplug.colorcorrect')


def correct_colors(img_path, factors):
    logger.debug("Correcting color of \"{0}\"".format(img_path))
    for channel, factor in zip(('red', 'green', 'blue'), factors):
        logger.debug("Correcting {0} channel by {1}"
                     .format(channel, factor))
        with wand.image.Image(filename=img_path) as img:
            wand.api.libmagick.MagickEvaluateImageChannel(
                img.wand, wand.image.CHANNELS[channel],
                wand.image.EVALUATE_OPS.index('multiply'),
                factor)
            img.save(filename=img_path)


class ColorCorrectionPlugin(HookPlugin):
    def process(self, path):
        path = os.path.join(path, 'raw')
        logger.debug("Starting color correction...")
        # Get the gray card's RGB values from configuration
        true_colors = (float(self.config['colorcorrect']['true_red']
                             .get(int)),
                       float(self.config['colorcorrect']['true_green']
                             .get(int)),
                       float(self.config['colorcorrect']['true_blue']
                             .get(int))
                       )
        # We assume that the first two images shot were the gray card
        images = sorted([os.path.join(path, x) for x in os.listdir(path)])
        factors_left = map(operator.div, true_colors,
                           self._get_color(images[0]))
        factors_right = map(operator.div, true_colors,
                            self._get_color(images[1]))

        with futures.ProcessPoolExecutor() as executor:
            # Don't correct the pictures with the gray cards
            for idx, img in enumerate(images[3:]):
                if not idx % 2:
                    factors = factors_left
                else:
                    factors = factors_right
                executor.submit(correct_colors, img, factors)

    def _get_color(self, img_path):
        """ Get average color of image's core 500x500 area. """
        with wand.image.Image(filename=img_path) as img:
            img.crop(left=img.size[0]/2-250,
                     top=img.size[1]/2-250,
                     width=500, height=500)           # crop rectangle
            img.resize(1, 1)
            color = (img[0][0].red_int8, img[0][0].green_int8,
                     img[0][0].blue_int8)
        return color

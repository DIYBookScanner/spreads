import logging
import operator
import os

import wand.api
import wand.image

from spreads.plugin import HookPlugin
from spreads.util import run_multicore


class ColorCorrectionPlugin(HookPlugin):
    def __init__(self, config):
        self.config = config['postprocess']['colorcorrect']

    def process(self, path):
        path = os.path.join(path, 'raw')
        logging.debug("Starting color correction...")
        # Get the gray card's RGB values from configuration
        true_colors = (float(self.config['true_red'].get(int)),
                       float(self.config['true_green'].get(int)),
                       float(self.config['true_blue'].get(int)))
        # We assume that the first two images shot were the gray card
        images = sorted([os.path.join(path, x) for x in os.listdir(path)])
        factors_left = map(operator.div, true_colors,
                           self._get_color(images[0]))
        factors_right = map(operator.div, true_colors,
                            self._get_color(images[1]))

        # NOTE: This would be an obvious candidate to run on multiple cores,
        #       but for some reason it gets stuck after correcting the first
        #       channel, so here's a single core implementation...
        for idx, img in enumerate(images[3:]):
            if not idx % 2:
                factors = factors_left
            else:
                factors = factors_right
            self._correct_colors(img, factors)

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

    def _correct_colors(self, img_path, factors):
        logging.debug("Correcting color of \"{0}\"".format(img_path))
        for channel, factor in zip(('red', 'green', 'blue'), factors):
            logging.debug("Correcting {0} channel by {1}"
                          .format(channel, factor))
            with wand.image.Image(filename=img_path) as img:
                wand.api.libmagick.MagickEvaluateImageChannel(
                    img.wand, wand.image.CHANNELS[channel],
                    wand.image.EVALUATE_OPS.index('multiply'),
                    factor)
                img.save(filename=img_path)

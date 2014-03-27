# -*- coding: utf-8 -*-

import logging

from concurrent import futures
from jpegtran import JPEGImage

from spreads.plugin import (HookPlugin, ProcessHookMixin, progress)

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
    rotated.save(path)


class AutoRotatePlugin(HookPlugin, ProcessHookMixin):
    __name__ = 'autorotate'

    def process(self, path):
        img_dir = path / 'raw'
        logger.info("Rotating images in {0}".format(img_dir))
        with futures.ProcessPoolExecutor() as executor:
            files = sorted(img_dir.iterdir())
            num_total = len(files)
            for (idx, imgpath) in enumerate(files):
                if imgpath.suffix.lower() not in ('.jpg', '.jpeg'):
                    continue
                future = executor.submit(autorotate_image, unicode(imgpath))
                future.add_done_callback(lambda x: progress.send(
                    sender=self,
                    progress=float(idx)/num_total
                ))

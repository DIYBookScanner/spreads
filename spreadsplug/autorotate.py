# -*- coding: utf-8 -*-

import logging

from concurrent import futures

from spreads.plugin import HookPlugin, ProcessHookMixin

logger = logging.getLogger('spreadsplug.autorotate')

try:
    from jpegtran import JPEGImage

    def autorotate_image(path):
        img = JPEGImage(path)
        if img.exif_orientation is None:
            logger.warn(
                "Image {0} did not have any EXIF rotation, did not rotate."
                .format(path))
            return
        elif img.exif_orientation == 1:
            logger.info("Image {0} is already rotated.".format(path))
            return
        rotated = img.exif_autotransform()
        rotated.save(path)
except ImportError:
    import PIL
    import pyexiv2

    def autorotate_image(path):
        try:
            metadata = pyexiv2.ImageMetadata(path)
            metadata.read()
            orient = int(metadata['Image.Exif.Orientation'])
        except:
            logger.warn(
                "Image {0} did not have any EXIF rotation, did not rotate."
                .format(path))
            return

        img = PIL.Image(path)
        if orient == 1:
            logger.info("Image {0} is already rotated.".format(path))
            return
        elif orient == 2:
            img.flip(PIL.Image.FLIP_LEFT_RIGHT)
        elif orient == 3:
            img.flip(PIL.Image.ROTATE_180)
        elif orient == 4:
            img.flip(PIL.Image.FLIP_TOP_BOTTOM)
        elif orient == 5:
            img.flip(PIL.Image.ROTATE_90)
            img.flip(PIL.Image.FLIP_LEFT_RIGHT)
        elif orient == 6:
            img.flip(PIL.Image.ROTATE_90)
        elif orient == 7:
            img.flip(PIL.Image.ROTATE_270)
            img.flip(PIL.Image.FLIP_LEFT_RIGHT)
        elif orient == 8:
            img.flip(PIL.Image.ROTATE_270)
        img.save(path)


class AutoRotatePlugin(HookPlugin, ProcessHookMixin):
    __name__ = 'autorotate'

    def _get_progress_callback(self, idx, num_total):
        return lambda x: self.on_progressed.send(
            self,
            progress=float(idx)/num_total)

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
                future.add_done_callback(
                    self._get_progress_callback(idx, num_total)
                )

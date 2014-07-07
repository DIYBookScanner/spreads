# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

import logging
import shutil

from concurrent.futures import ProcessPoolExecutor

from spreads.plugin import HookPlugin, ProcessHookMixin

logger = logging.getLogger('spreadsplug.autorotate')

try:
    from jpegtran import JPEGImage

    def autorotate_image(in_path, out_path):
        img = JPEGImage(in_path)
        if img.exif_orientation is None:
            logger.warn(
                "Image {0} did not have any EXIF rotation, did not rotate."
                .format(in_path))
            return
        elif img.exif_orientation == 1:
            logger.info("Image {0} is already rotated.".format(in_path))
            shutil.copyfile(in_path, out_path)
        else:
            rotated = img.exif_autotransform()
            rotated.save(out_path)
except ImportError:
    import pyexiv2
    from wand.image import Image

    def autorotate_image(in_path, out_path):
        try:
            metadata = pyexiv2.ImageMetadata(in_path)
            metadata.read()
            orient = int(metadata['Exif.Image.Orientation'].value)
        except:
            logger.warn(
                "Image {0} did not have any EXIF rotation, did not rotate."
                .format(in_path))
            return

        img = Image(filename=in_path)
        if orient == 1:
            logger.info("Image {0} is already rotated.".format(in_path))
            shutil.copyfile(in_path, out_path)
            return
        elif orient == 2:
            img.flip()
        elif orient == 3:
            img.rotate(180)
        elif orient == 4:
            img.flop()
        elif orient == 5:
            img.rotate(90)
            img.flip()
        elif orient == 6:
            img.rotate(90)
        elif orient == 7:
            img.rotate(270)
            img.flip()
        elif orient == 8:
            img.rotate(270)
        img.save(filename=out_path)


class AutoRotatePlugin(HookPlugin, ProcessHookMixin):
    __name__ = 'autorotate'

    def _get_progress_callback(self, idx, num_total):
        return lambda x: self.on_progressed.send(
            self,
            progress=float(idx)/num_total)

    def _get_update_callback(self, page, out_path):
        return lambda x: page.processed_images.update(
            {self.__name__: out_path})

    def process(self, pages, target_path):
        logger.info("Rotating images")
        futures = []
        with ProcessPoolExecutor() as executor:
            num_total = len(pages)
            for (idx, page) in enumerate(pages):
                in_path = page.get_latest_processed(image_only=True)
                if in_path is None:
                    in_path = page.raw_image
                if in_path.suffix.lower() not in ('.jpg', '.jpeg'):
                    logger.warn("Image {0} is not a JPG file, cannot be "
                                "rotated".format(in_path))
                    continue
                out_path = target_path/(in_path.stem + "_rotated.jpg")
                future = executor.submit(autorotate_image,
                                         unicode(in_path),
                                         unicode(out_path))
                future.add_done_callback(
                    self._get_progress_callback(idx, num_total)
                )
                future.add_done_callback(
                    self._get_update_callback(page, out_path)
                )
                futures.append(future)

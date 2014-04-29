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

from concurrent import futures
from jpegtran import JPEGImage

from spreads.plugin import HookPlugin, ProcessHookMixin

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

    def _get_progress_callback(self, idx, num_total):
        return lambda x: self.on_progressed.send(
            self,
            progress=float(idx)/num_total)

    def process(self, path):
        img_dir = path / 'data' / 'raw'
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

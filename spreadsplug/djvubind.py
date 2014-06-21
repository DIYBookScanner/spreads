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

from __future__ import division, unicode_literals

import logging
import os
import shutil
import subprocess
import tempfile

from spreads.vendor.pathlib import Path

from spreads.plugin import HookPlugin, OutputHookMixin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('djvubind'):
    raise MissingDependencyException("Could not find executable `djvubind` in"
                                     " $PATH. Please install the appropriate"
                                     " package(s)!")

logger = logging.getLogger('spreadsplug.djvubind')


class DjvuBindPlugin(HookPlugin, OutputHookMixin):
    __name__ = 'djvubind'

    # TODO: Adapt to new API
    def output(self, pages, target_path, metadata, table_of_contents):
        logger.info("Assembling DJVU.")

        tmpdir = Path(tempfile.mkdtemp())
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            link_path = (tmpdir/fpath.name)
            link_path.symlink_to(fpath)

        djvu_file = target_path/"book.djvu"
        cmd = ["djvubind", unicode(tmpdir), '--no-ocr']
        logger.debug("Running " + " ".join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        os.rename("book.djvu", unicode(djvu_file))
        shutil.rmtree(unicode(tmpdir))

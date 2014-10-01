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

""" Plugin that creates a DJVU file from a workflow's pages.

If there is hOCR data for a page, a hidden OCR-layer will be included.
"""

from __future__ import division, unicode_literals

import logging
import os
import shutil
import subprocess
import tempfile

from spreads.vendor.pathlib import Path

from spreads.plugin import HookPlugin, OutputHooksMixin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('djvubind'):
    raise MissingDependencyException("Could not find executable `djvubind`. "
                                     "Please install the appropriate "
                                     "package(s)!")

logger = logging.getLogger('spreadsplug.djvubind')


class DjvuBindPlugin(HookPlugin, OutputHooksMixin):
    __name__ = 'djvubind'

    def output(self, pages, target_path, metadata, table_of_contents):
        """ Go through pages and bundle their most recent images into a DJVU
            file.

        :param pages:               Pages to bundle
        :param target_path:         list of :py:class:`spreads.workflow.Page`
        :param metadata:            Metadata to include in DJVU file
        :type metadata:             :py:class:`spreads.metadata.Metadata`
        :param table_of_contents:   Table of contents to include in DJVU file
        :type table_of_contents:    list of :py:class:`TocEntry`
        """
        logger.info("Assembling DJVU.")

        tmpdir = Path(tempfile.mkdtemp())
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            link_path = (tmpdir/fpath.name)
            link_path.symlink_to(fpath)

        # TODO: Add metadata
        # TODO: Add table of contents

        djvu_file = target_path/"book.djvu"
        cmd = ["djvubind", unicode(tmpdir), '--no-ocr']
        logger.debug("Running " + " ".join(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        os.rename("book.djvu", unicode(djvu_file))
        shutil.rmtree(unicode(tmpdir))

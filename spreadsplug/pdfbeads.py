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
import time

from spreads.vendor.pathlib import Path

from spreads.plugin import HookPlugin, OutputHookMixin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('pdfbeads'):
    raise MissingDependencyException("Could not find executable `pdfbeads`."
                                     "Please install the appropriate "
                                     "package(s)!")

logger = logging.getLogger('spreadsplug.pdfbeads')


class PDFBeadsPlugin(HookPlugin, OutputHookMixin):
    __name__ = 'pdfbeads'

    def output(self, pages, target_path, metadata, table_of_contents):
        logger.info("Assembling PDF.")

        tmpdir = Path(tempfile.mkdtemp())
        # NOTE: pdfbeads only finds *html files for the text layer in the
        #       working directory, so we have to chdir() into it
        old_path = os.path.abspath(os.path.curdir)
        os.chdir(unicode(tmpdir))

        images = []
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            link_path = (tmpdir/fpath.name)
            link_path.symlink_to(fpath)
            if 'tesseract' in page.processed_images:
                ocr_path = page.processed_images['tesseract']
                (tmpdir/ocr_path.name).symlink_to(ocr_path)
            images.append(link_path)

        # TODO: Use metadata to create a METAFILE for pdfbeads
        # TODO: Use table_of_contents to create a TOCFILE for pdfbeads
        # TODO: Use page.page_label to create a LSPEC for pdfbeads

        pdf_file = target_path/"book.pdf"
        cmd = ["pdfbeads", "-d"]
        cmd.extend([f.name for f in images])
        cmd.extend(["-o", unicode(pdf_file)])
        logger.debug("Running " + " ".join(cmd))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        last_count = 0
        while proc.poll() is None:
            current_count = sum(1 for x in tmpdir.glob('*.jbig2'))
            if current_count > last_count:
                last_count = current_count
                self.on_progressed.send(
                    self, progress=float(current_count)/len(images))
            time.sleep(.01)
        logger.debug("Output:\n{0}".format(proc.stdout.read()))
        os.chdir(old_path)
        #shutil.rmtree(unicode(tmpdir))

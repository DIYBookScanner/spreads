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

""" Plugin that creates a PDF file from a workflow's pages.

Page images will be separated into a black-and-white text layer that is
compressed with JBIG2 and an image layer that is compressed with JPEG2000.

If there is hOCR data for a page, a hidden OCR-layer will be included.
"""

from __future__ import division, unicode_literals

import codecs
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time

from pathlib import Path

import spreads.util as util
from spreads.plugin import HookPlugin, OutputHooksMixin

BIN = util.find_in_path('pdfbeads')
IS_WIN = util.is_os('windows')

if not BIN:
    raise util.MissingDependencyException(
        "Could not find executable `pdfbeads`. Please install the appropriate "
        "package(s)!")


logger = logging.getLogger('spreadsplug.pdfbeads')


class PDFBeadsPlugin(HookPlugin, OutputHooksMixin):
    __name__ = 'pdfbeads'

    def output(self, pages, target_path, metadata, table_of_contents):
        """ Go through pages and bundle their most recent images into a PDF
            file.

        :param pages:               Pages to bundle
        :param target_path:         list of :py:class:`spreads.workflow.Page`
        :param metadata:            Metadata to include in PDF file
        :type metadata:             :py:class:`spreads.metadata.Metadata`
        :param table_of_contents:   Table of contents to include in PDF file
        :type table_of_contents:    list of :py:class:`TocEntry`
        """
        logger.info("Assembling PDF.")

        tmpdir = Path(tempfile.mkdtemp())

        meta_file = tmpdir/'metadata.txt'
        with codecs.open(unicode(meta_file), "w", "utf-8") as fp:
            for key, value in metadata.iteritems():
                if key == 'title':
                    fp.write("Title: \"{0}\"\n".format(value))
                if key == 'creator':
                    for author in value:
                        fp.write("Author: \"{0}\"\n".format(author))

        images = []
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            link_path = (tmpdir/fpath.name)
            if IS_WIN:
                shutil.copy(unicode(fpath), unicode(link_path))
            else:
                link_path.symlink_to(fpath.absolute())
            if 'tesseract' in page.processed_images:
                ocr_path = page.processed_images['tesseract']
                if IS_WIN:
                    shutil.copy(unicode(ocr_path),
                                unicode(tmpdir/ocr_path.name))
                else:
                    (tmpdir/ocr_path.name).symlink_to(ocr_path.absolute())
            images.append(link_path.absolute())

        pdf_file = target_path.absolute()/"book.pdf"

        # TODO: Use table_of_contents to create a TOCFILE for pdfbeads
        # TODO: Use page.page_label to create a LSPEC for pdfbeads

        # NOTE: pdfbeads only finds *html files for the text layer in the
        #       working directory, so we have to chdir() into it
        old_path = os.path.abspath(os.path.curdir)
        os.chdir(unicode(tmpdir))

        cmd = [BIN, "-d", "-M", unicode(meta_file)]
        if IS_WIN:
            cmd.append(util.wildcardify(tuple(f.name for f in images)))
        else:
            cmd.extend([unicode(f) for f in images])
        cmd.extend(["-o", unicode(pdf_file)])
        logger.debug("Running " + " ".join(cmd))
        proc = util.get_subprocess(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=IS_WIN)
        if IS_WIN:
            # NOTE: Due to a bug in the jbig2enc version for Windows, the error
            #       output gets huge, creating a deadlock. Hence, we go the
            #       safe way and use `communicate()`, though this means no
            #       progress notification for the user.
            output, errors = proc.communicate()
        else:
            errors = ""
            is_jbig2 = False
            cur_jbig2_page = 0
            while proc.poll() is None:
                cur_line = proc.stderr.readline()
                errors += "\n" + cur_line
                prep_match = re.match(r"^Prepared data for processing (.*)$",
                                      cur_line)
                proc_match = re.match(r"^Processed (.*)$", cur_line)
                jbig2_match = re.match(
                    r"^JBIG2 compression complete. pages:(\d+) symbols:\d+ "
                    r"log2:\d+$", cur_line)
                progress = None
                if prep_match:
                    file_idx = next(idx for idx, f in enumerate(images)
                                    if unicode(f) == prep_match.group(1))
                    progress = file_idx/(len(images)*2)
                elif jbig2_match:
                    cur_jbig2_page += int(jbig2_match.group(1))
                    progress = (len(images) + cur_jbig2_page) / (len(images)*2)
                    is_jbig2 = True
                elif proc_match and not is_jbig2:
                    file_idx = next(idx for idx, f in enumerate(images)
                                    if unicode(f) == proc_match.group(1))
                    progress = (len(images) + file_idx)/(len(images)*2)
                if progress is not None:
                    self.on_progressed.send(self, progress=progress)
                time.sleep(.01)
            output = proc.stdout.read()
        logger.debug("pdfbeads stdout:\n{0}".format(output))
        logger.debug("pdfbeads stderr:\n{0}".format(errors))
        os.chdir(old_path)
        shutil.rmtree(unicode(tmpdir))

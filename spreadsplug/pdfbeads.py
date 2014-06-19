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
import subprocess
import time

from spreads.plugin import HookPlugin, OutputHookMixin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('pdfbeads'):
    raise MissingDependencyException("Could not find executable `pdfbeads` in"
                                     " $PATH. Please install the appropriate"
                                     " package(s)!")

logger = logging.getLogger('spreadsplug.pdfbeads')


class PDFBeadsPlugin(HookPlugin, OutputHookMixin):
    __name__ = 'pdfbeads'

    def output(self, path):
        logger.info("Assembling PDF.")
        path = path.absolute()
        img_dir = path / 'data' / 'done'
        pdf_file = path / 'data' / 'out' / "{0}.pdf".format(path.name)
        img_files = [unicode(x.name) for x in sorted(img_dir.glob('*.tif'))]
        cmd = ["pdfbeads", "-d"] + img_files + ["-o", unicode(pdf_file)]
        logger.debug("Running " + " ".join(cmd))
        # NOTE: pdfbeads only finds *html files for the text layer in the
        #       working directory...
        os.chdir(unicode(img_dir))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        last_count = 0
        while proc.poll() is None:
            current_count = sum(1 for x in img_dir.glob('*.jbig2'))
            if current_count > last_count:
                last_count = current_count
                self.on_progressed.send(
                    self, progress=float(current_count)/len(img_files))
            time.sleep(.1)
        logger.debug("Output:\n{0}".format(proc.stdout.read()))

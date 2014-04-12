# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import os
import subprocess
import time

from spreads.plugin import HookPlugin, OutputHookMixin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('pdfbeads'):
    raise MissingDependencyException("Could not find executable `pdfbeads`."
                                     "Please install the appropriate "
                                     "package(s)!")

logger = logging.getLogger('spreadsplug.pdfbeads')


class PDFBeadsPlugin(HookPlugin, OutputHookMixin):
    __name__ = 'pdfbeads'

    def output(self, path):
        logger.info("Assembling PDF.")
        path = path.absolute()
        img_dir = path / 'done'
        pdf_file = path / 'out' / "{0}.pdf".format(path.name)
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

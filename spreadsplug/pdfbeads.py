# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import os
import subprocess

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
        img_dir = path / 'done'
        pdf_file = path / 'out' / "{0}.pdf".format(path.name)
        img_files = [unicode(x.name) for x in sorted(img_dir.glob('*.tif'))]
        cmd = ["pdfbeads", "-d"] + img_files + ["-o", unicode(pdf_file)]
        logger.debug("Running " + " ".join(cmd))
        # NOTE: pdfbeads only finds *html files for the text layer in the
        #       working directory...
        os.chdir(unicode(img_dir))
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        logger.debug("Output:\n{0}".format(output))

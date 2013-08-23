# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import os
import subprocess

from spreads.plugin import HookPlugin
from spreads.util import MissingDependencyException, find_in_path

if not find_in_path('pdfbeads'):
    raise MissingDependencyException("Could not find executable `pdfbeads` in"
                                     " $PATH. Please install the appropriate"
                                     " package(s)!")

logger = logging.getLogger('spreadsplug.pdfbeads')


class PDFBeadsPlugin(HookPlugin):
    def output(self, path):
        logger.info("Assembling PDF.")
        img_dir = os.path.join(path, 'done')
        pdf_file = os.path.join('..', 'out',
                                "{0}.pdf".format(os.path.basename(path)))
        img_files = [x
                     for x in sorted(os.listdir(img_dir))
                     if os.path.splitext(x)[1].lower() == '.tif']
        cmd = ["pdfbeads", "-d"] + img_files + ["-o", pdf_file]
        logger.debug("Running " + " ".join(cmd))
        # NOTE: pdfbeads only finds *html files for the text layer in the
        #       working directory...
        os.chdir(img_dir)
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

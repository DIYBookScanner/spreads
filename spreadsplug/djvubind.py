# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import os
import subprocess

from spreads.plugin import HookPlugin
from spreads.util import SpreadsException, find_in_path


class DjvuBindPlugin(HookPlugin):
    def process(self, path):
        if not find_in_path('djvubind'):
            raise SpreadsException("Could not find executable `djvubind` in"
                                   " $PATH. Please install the appropriate"
                                   " package(s)!")
        logging.info("Assembling DJVU.")
        img_dir = os.path.join(path, 'done')
        djvu_file = os.path.join(path,
                                 "{0}.djvu".format(os.path.basename(path)))
        cmd = ["djvubind", img_dir]
        if self.config['ocr'].get(unicode) == 'none':
            cmd.append("--no-ocr")
        logging.debug("Running " + " ".join(cmd))
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        os.rename("book.djvu", djvu_file)

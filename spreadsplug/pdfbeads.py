import logging
import os
import subprocess

from spreads.plugin import FilterPlugin
from spreads.util import SpreadsException, find_in_path


class PDFBeadsFilter(FilterPlugin):
    config_key = 'pdfbeads'

    def process(self, path):
        if not find_in_path('pdfbeads'):
            raise SpreadsException("Could not find executable `pdfbeads` in"
                                   " $PATH. Please install the appropriate"
                                   " package(s)!")
        logging.info("Assembling PDF.")
        img_dir = os.path.join(path, 'done')
        pdf_file = os.path.join(path, "{0}.pdf".format(os.path.basename(path)))
        img_files = [os.path.join(img_dir, x)
                     for x in os.listdir(img_dir)
                     if x.lower().endswith('tif')]
        cmd = ["pdfbeads"] + img_files + ["-o", pdf_file]
        logging.debug("Running " + " ".join(cmd))
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

import logging
import os
import re

import subprocess
from concurrent import futures

from spreads.plugin import HookPlugin

logger = logging.getLogger('spreadsplug.tesseract')


class TesseractPlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == 'postprocess':
            parser.add_argument("--language", "-l",
                                dest="language", action="store_true",
                                help="OCR language (3-letter language code")

    def __init__(self, config):
        self.config = config['postprocess']

    def process(self, path):
        logger.info("Performing OCR")
        img_dir = os.path.join(path, 'done')
        with futures.ProcessPoolExecutor() as executor:
            for img in os.listdir(img_dir):
                if not img.endswith('tif'):
                    continue
                executor.submit(
                    subprocess.check_call,
                    ["tesseract", os.path.join(img_dir, img),
                     os.path.join(img_dir, os.path.splitext(img)[0]),
                     "-l", "fra", "hocr"],
                    stderr=subprocess.STDOUT
                )
        # NOTE: This modifies the hOCR files to make them compatible with
        #       pdfbeads.
        #       See the following bugreport for more information:
        #       http://rubyforge.org/tracker/index.php?func=detail&aid=29737&group_id=9752&atid=37737
        for hocr in os.listdir(img_dir):
            if not hocr.endswith('html'):
                continue
            fname = os.path.join(img_dir, hocr)
            with open(fname, 'r') as fp:
                new_content = re.sub(r'(<span[^>]*>(<strong>)? +(<\/strong>)?'
                                     r'<\/span>*)(<span[^>]*>(<strong>)? '
                                     r'+(<\/strong>)?<\/span> *)',
                                     r'\g<1>', fp.read())
            with open(fname, 'w') as fp:
                fp.write(new_content)

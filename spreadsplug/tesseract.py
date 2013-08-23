import logging
import os
import re
import subprocess
import xml.etree.cElementTree as ET

from concurrent import futures

from spreads.plugin import HookPlugin
from spreads.util import find_in_path, MissingDependencyException

if not find_in_path('tesseract'):
    raise MissingDependencyException("Could not find executable `tesseract`"
                                     " in $PATH. Please install the"
                                     " appropriate package(s)!")

logger = logging.getLogger('spreadsplug.tesseract')


class TesseractPlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == 'postprocess':
            parser.add_argument("--language", "-l",
                                dest="language", default="eng",
                                help="OCR language (3-letter language code)"
                                     " [default: eng]")

    def process(self, path):
        ocr_lang = self.config['language'].get(str)
        logger.info("Performing OCR")
        logger.info("Language is \"{0}\"".format(ocr_lang))
        img_dir = os.path.join(path, 'done')
        with futures.ProcessPoolExecutor() as executor:
            for img in os.listdir(img_dir):
                if not img.endswith('tif'):
                    continue
                executor.submit(
                    subprocess.check_call,
                    ["tesseract", os.path.join(img_dir, img),
                     os.path.join(img_dir, os.path.splitext(img)[0]),
                     "-l", ocr_lang, "hocr"],
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

    def output(self, path):
        outfile = os.path.join(path, 'out', "{0}.hocr"
                                            .format(os.path.basename(path)))
        path = os.path.join(path, 'done')
        out_root = ET.Element('html')
        ET.SubElement(out_root, 'head')
        body = ET.SubElement(out_root, 'body')

        for idx, page in enumerate(sorted([os.path.join(path, x)
                                   for x in os.listdir(path)
                                   if x.endswith('.html')])):
            # NOTE: Fixe some things from hOCR output so we can parse it...
            with open(page, 'r+') as fp:
                content = re.sub(r'<em><\/em>', '', fp.read())
                content = re.sub(r'<strong><\/strong>', '', content)
            page = ET.fromstring(content)
            page_elem = page.find("xhtml:body/xhtml:div[@class='ocr_page']",
                                  dict(xhtml="http://www.w3.org/1999/xhtml"))
            # Correct page_number
            page_elem.set('id', 'page_{0}'.format(idx))

            # And tack it onto the output file
            if page_elem:
                body.append(page_elem)
        with open(outfile, 'w') as fp:
            # Strip those annoying namespace tags...
            out_string = re.sub(r"(<\/*)html:", "\g<1>",
                                ET.tostring(out_root))
            fp.write(out_string.encode("UTF-8"))

import logging
import multiprocessing
import os
import re
import subprocess
import time
import xml.etree.cElementTree as ET

from spreads.plugin import HookPlugin, ProcessHookMixin, PluginOption
from spreads.util import find_in_path, MissingDependencyException
from spreads.vendor.pathlib import Path

if not find_in_path('tesseract'):
    raise MissingDependencyException("Could not find executable `tesseract`"
                                     " in $PATH. Please install the"
                                     " appropriate package(s)!")

logger = logging.getLogger('spreadsplug.tesseract')
try:
    AVAILABLE_LANGS = (subprocess.check_output(["tesseract", "--list-langfoo"],
                                               stderr=subprocess.STDOUT)
                       .split("\n")[1:-1])
except subprocess.CalledProcessError:
    AVAILABLE_LANGS = [x.stem for x in
                       Path('/usr/share/tesseract-ocr/tessdata')
                       .glob('*.traineddata')]


class TesseractPlugin(HookPlugin, ProcessHookMixin):
    __name__ = 'tesseract'

    @classmethod
    def configuration_template(cls):
        conf = {'language': PluginOption(value=AVAILABLE_LANGS,
                                         docstring="OCR language",
                                         selectable=True),
                }
        return conf

    def process(self, path):
        # TODO: This plugin should be 'output' only, since we ideally work
        #       with fully binarized output images
        logger.info("Performing OCR")
        img_dir = path / 'done'
        self._perform_ocr(img_dir, self.config["language"].get())
        for fname in img_dir.glob('*.html'):
            self._fix_hocr(fname)

    def _perform_ocr(self, img_dir, language):
        def _clean_processes(procs):
            for p in processes[:]:
                if p.poll() is not None:
                    processes.remove(p)

        language = self.config['language'].get()
        logger.info("Language is \"{0}\"".format(language))
        processes = []
        max_procs = multiprocessing.cpu_count()
        FNULL = open(os.devnull, 'w')
        for img in img_dir.glob('*.tif'):
            # Wait until another process has finished
            while len(processes) >= max_procs:
                _clean_processes(processes)
                time.sleep(0.01)
            proc = subprocess.Popen(["tesseract", unicode(img),
                                    unicode(img_dir / img.stem), "-l",
                                    language, "hocr"], stderr=FNULL,
                                    stdout=FNULL)
            processes.append(proc)
        # Wait for remaining processes to finish
        while processes:
            _clean_processes(processes)

    def _fix_hocr(self, fpath):
        # NOTE: This modifies the hOCR files to make them compatible with
        #       pdfbeads.
        #       See the following bugreport for more information:
        #       http://rubyforge.org/tracker/index.php?func=detail&aid=29737&group_id=9752&atid=37737
        with fpath.open('r') as fp:
            new_content = re.sub(r'(<span[^>]*>(<strong>)? +(<\/strong>)?'
                                 r'<\/span> *)(<span[^>]*>(<strong>)? '
                                 r'+(<\/strong>)?<\/span> *)',
                                 r'\g<1>', fp.read())
        with fpath.open('w') as fp:
            fp.write(new_content)

    def output(self, path):
        outfile = path / 'out' / "{0}.hocr".format(path.name)
        inpath = path / 'done'
        out_root = ET.Element('html')
        ET.SubElement(out_root, 'head')
        body = ET.SubElement(out_root, 'body')

        for idx, page in enumerate(sorted(inpath.glob('*.html'))):
            # NOTE: Fixe some things from hOCR output so we can parse it...
            with page.open('r+') as fp:
                content = re.sub(r'<em><\/em>', '', fp.read())
                content = re.sub(r'<strong><\/strong>', '', content)
            page = ET.fromstring(content.encode('utf-8'))
            page_elem = page.find("xhtml:body/xhtml:div[@class='ocr_page']",
                                  dict(xhtml="http://www.w3.org/1999/xhtml"))
            # Correct page_number
            page_elem.set('id', 'page_{0}'.format(idx))

            # And tack it onto the output file
            if page_elem:
                body.append(page_elem)
        with outfile.open('w') as fp:
            # Strip those annoying namespace tags...
            out_string = re.sub(r"(<\/*)html:", "\g<1>",
                                ET.tostring(out_root))
            fp.write(unicode(out_string))

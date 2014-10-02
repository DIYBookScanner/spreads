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

""" Postprocessing plugin that runs a workflow's images through optical
    character recognition (by using tesseract).

The output is saved as hOCR files that can be used by other plugins (e.g.
:py:module:`spreadsplug.djvubind` and :py:module:`spreadsplug.pdfbeads`)
"""

import logging
import multiprocessing
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.cElementTree as ET
from itertools import chain

import spreads.util as util
from spreads.config import OptionTemplate
from spreads.plugin import HookPlugin, ProcessHooksMixin
from spreads.vendor.pathlib import Path

BIN = util.find_in_path('tesseract')
if not BIN:
    raise util.MissingDependencyException(
        "Could not find executable `tesseract`. Please install the appropriate"
        " package(s)!")

# Newer versions of Tesseract provide a flag to obtain a list of installed
# OCR languages, for older versions we have to read out the directory
# containing the training data for languages.
try:
    AVAILABLE_LANGS = (util.get_subprocess([BIN, "--list-langs"],
                                           stderr=subprocess.STDOUT,
                                           stdout=subprocess.PIPE)
                       .communicate()[0]
                       .split("\n")[1:-1])
    # There should be at least a single language
    if not AVAILABLE_LANGS:
        raise ValueError()
except (subprocess.CalledProcessError, ValueError):
    AVAILABLE_LANGS = [x.stem for x in
                       Path('/usr/share/tesseract-ocr/tessdata')
                       .glob('*.traineddata')]

logger = logging.getLogger('spreadsplug.tesseract')


class TesseractPlugin(HookPlugin, ProcessHooksMixin):
    __name__ = 'tesseract'

    @classmethod
    def configuration_template(cls):
        conf = {'language': OptionTemplate(value=AVAILABLE_LANGS,
                                           docstring="OCR language",
                                           selectable=True),
                }
        return conf

    def process(self, pages, target_path):
        """ For each page, rotate the most recent image according to its EXIF
            orientation tag.

        :param pages:       Pages to be processed
        :type pages:        list of :py:class:`spreads.workflow.Page`
        :param target_path: Base directory where processed images are to be
                            stored
        :type target_path:  :py:class:`pathlib.Path`
        """
        # TODO: This plugin should be 'output' only, since we ideally work
        #       with fully binarized output images

        # Map input paths to their pages so we can more easily associate
        # the generated output files with their pages later on
        in_paths = {}
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            in_paths[fpath] = page

        out_dir = Path(tempfile.mkdtemp(prefix='tess-out'))
        language = self.config["language"].get()

        logger.info("Performing OCR")
        logger.info("Language is \"{0}\"".format(language))
        self._perform_ocr(in_paths, out_dir, language)

        for fname in chain(out_dir.glob('*.hocr'), out_dir.glob('*.html')):
            self._perform_replacements(fname)
            # For each hOCR file, try to find a corresponding input image
            # and associate it to the image's page
            out_stem = fname.stem
            for in_path, page in in_paths.iteritems():
                if in_path.stem == out_stem:
                    target_fname = target_path/fname.name
                    shutil.copyfile(unicode(fname), unicode(target_fname))
                    page.processed_images[self.__name__] = target_fname
                    break
            else:
                logger.warn("Could not find page for output file {0}"
                            .format(fname))

    def _perform_ocr(self, in_paths, out_dir, language):
        """ For each input image, launch tesseract and keep track of how far
            along the work is.

        :param in_paths:    Input images
        :type in_paths:     list of :py:class:`pathlib.Path`
        :param out_dir:     Output directory for hOCR files
        :type out_dir:      :py:class:`pathlib.Path`
        :param language:    Language to use for OCRing, must be among tesseract
                            languages installed on the system.
        :type language:     unicode
        """
        processes = []

        def _clean_processes():
            """ Go through processes, remove completed and emit a
                :py:attr:`on_progressed` signal for it.
            """
            for p in processes[:]:
                if p.poll() is not None:
                    processes.remove(p)
                    _clean_processes.num_cleaned += 1
                    self.on_progressed.send(
                        self, progress=float(_clean_processes
                                             .num_cleaned)/len(in_paths))
        _clean_processes.num_cleaned = 0

        # Run as many simultaneous Tesseract instances as there are CPU cores
        max_procs = multiprocessing.cpu_count()
        FNULL = open(os.devnull, 'w')
        for fpath in in_paths:
            # Wait until another process has finished
            while len(processes) >= max_procs:
                _clean_processes()
                time.sleep(0.01)
            cmd = [BIN, unicode(fpath), unicode(out_dir / fpath.stem),
                   "-l", language, "hocr"]
            logger.debug(cmd)
            proc = util.get_subprocess(cmd, stderr=FNULL, stdout=FNULL)
            processes.append(proc)
        # Wait for remaining processes to finish
        while processes:
            _clean_processes()

    def _perform_replacements(self, fpath):
        """ Perform user-supplied replacements on a hOCR file.

        :param fpath:   hOCR file to perform replacements on
        :type fpath:    :py:class:`pathlib.Path`
        """
        def get_flags(group):
            flags = 0
            if 'flags' not in group:
                return flags
            for flag in group['flags']:
                try:
                    flags |= RE_FLAGS[flag]
                except KeyError:
                    raise ValueError("Unknown flag: '{0}'".format(flag))
            return flags

        RE_FLAGS = {
            'debug': re.DEBUG,
            'ignorecase': re.IGNORECASE,
            'locale': re.LOCALE,
            'multiline': re.MULTILINE,
            'unicode': re.UNICODE,
        }
        with fpath.open('r') as fp:
            content = fp.read()
            # NOTE: This modifies the hOCR files to make them compatible with
            #       pdfbeads.
            #       See the following bugreport for more information:
            #       http://rubyforge.org/tracker/index.php?func=detail&\
            #       aid=29737&group_id=9752&atid=37737
            # FIXME: Somehow this does not work for some files, find out why
            content = re.sub(
                r'(<span[^>]*>(<strong>)? +(<\/strong>)?<\/span> *)'
                r'(<span[^>]*>(<strong>)? +(<\/strong>)?<\/span> *)',
                r'\g<1>', content)
            # Perform user-configured replacements
            if 'replacements' in self.config.keys():
                replacements = self.config['replacements'].get()
                for name, group in replacements.iteritems():
                    content = re.sub(group['regex'], group['substitution'],
                                     content, flags=get_flags(group))
        with fpath.open('w') as fp:
            fp.write(content)

    def output(self, pages, target_path, metadata, table_of_contents):
        """ Combine all processed hOCR files into a single output file.

        :param pages:               Pages for which hOCR files should be
                                    bundled
        :param target_path:         list of :py:class:`spreads.workflow.Page`
        :param metadata:            ignored
        :type metadata:             :py:class:`spreads.metadata.Metadata`
        :param table_of_contents:   ignored
        :type table_of_contents:    list of :py:class:`TocEntry`
        """
        outfile = target_path/"text.html"
        out_root = ET.Element('html')
        ET.SubElement(out_root, 'head')
        body = ET.SubElement(out_root, 'body')

        for page in pages:
            # NOTE: Fixes some things from hOCR output so we can parse it...
            hocr_file = page.processed_images.get('tesseract')
            if hocr_file is None:
                logger.warn("Could not find hOCR file for page {0}, skipping."
                            .format(page))
                continue
            with hocr_file.open('r+') as fp:
                content = re.sub(r'<em><\/em>', '', fp.read())
                content = re.sub(r'<strong><\/strong>', '', content)
            pagexml = ET.fromstring(content.encode('utf-8'))
            page_elem = pagexml.find(
                "xhtml:body/xhtml:div[@class='ocr_page']",
                dict(xhtml="http://www.w3.org/1999/xhtml"))
            # Correct page_number
            page_elem.set('id', 'page_{0}'.format(page.sequence_num))

            # And tack it onto the output file
            if page_elem:
                body.append(page_elem)
        with outfile.open('w') as fp:
            # Strip those annoying namespace tags...
            out_string = re.sub(r"(<\/*)html:", "\g<1>",
                                ET.tostring(out_root))
            fp.write(unicode(out_string))

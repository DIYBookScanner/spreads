# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import math
import multiprocessing
import os
import shutil
import subprocess
import tempfile
from xml.etree.cElementTree import ElementTree as ET

from spreads.plugin import HookPlugin
from spreads.util import find_in_path, MissingDependencyException

if not find_in_path('scantailor-cli'):
    raise MissingDependencyException("Could not find executable"
                                     " `scantailor-cli` in $PATH. Please"
                                     " install the appropriate package(s)!")

logger = logging.getLogger('spreadsplug.scantailor')


class ScanTailorPlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == "postprocess":
            parser.add_argument(
                "--auto", "-a", dest="autopilot", action="store_true",
                default=False,
                help="Don't prompt user to edit ScanTailor configuration")
            parser.add_argument(
                "--page-detection", "-pd", dest="page_detection",
                action="store_true", default=False,
                help="Use page for layout instead of content")

    def _generate_configuration(self, projectfile, img_dir, out_dir):
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        logger.info("Generating ScanTailor configuration")
        filterconf = [self.config['scantailor'][x].get(bool)
                      for x in ('rotate', 'split_pages', 'deskew', 'content',
                                'auto_margins')]
        start_filter = filterconf.index(True)+1
        end_filter = len(filterconf) - list(reversed(filterconf)).index(True)+1
        marginconf = self.config['scantailor']['margins'].as_str_seq()
        generation_cmd = ['scantailor-cli',
                          '--start-filter={0}'.format(start_filter),
                          '--end-filter={0}'.format(end_filter),
                          '--layout=1.5',
                          '--dpi={0}'.format(self.config['device']['dpi']
                                             .get(int)),
                          '-o={0}'.format(projectfile)]
        page_detection = (
            self.config['scantailor']['detection'] == 'page'
            or ('page_detection' in self.config.keys()
                and self.config['page_detection'].get(bool))
        )
        if page_detection:
            generation_cmd.extend([
                '--enable-page-detection',
                '--disable-content-detection',
                '--enable-fine-tuning'
            ])
        else:
            generation_cmd.extend([
                '--margins-top={0}'.format(marginconf[0]),
                '--margins-right={0}'.format(marginconf[1]),
                '--margins-bottom={0}'.format(marginconf[2]),
                '--margins-left={0}'.format(marginconf[3]),
            ])
        generation_cmd.extend([img_dir, out_dir])
        logger.debug(" ".join(generation_cmd))
        subprocess.call(generation_cmd)

    def _split_configuration(self, projectfile, temp_dir):
        num_pieces = multiprocessing.cpu_count()
        tree = ET(file=projectfile)
        num_files = len(tree.findall('./files/file'))
        splitfiles = []
        files_per_job = int(math.ceil(float(num_files)/num_pieces))
        for idx in xrange(num_pieces):
            tree = ET(file=projectfile)
            root = tree.getroot()
            start = idx*files_per_job
            end = start + files_per_job
            if end > num_files:
                end = None
            for elem in ('files', 'images', 'pages',
                         'file-name-disambiguation'):
                elem_root = root.find(elem)
                to_keep = elem_root.getchildren()[start:end]
                to_remove = [x for x in elem_root.getchildren()
                             if not x in to_keep]
                for node in to_remove:
                    elem_root.remove(node)
            out_file = os.path.join(temp_dir,
                                    "{0}-{1}.ScanTailor".format(
                                    os.path.splitext(os.path.basename(
                                    projectfile))[0], idx))
            tree.write(out_file)
            splitfiles.append(out_file)
        return splitfiles

    def _generate_output(self, projectfile, out_dir):
        logger.debug("Generating output...")
        temp_dir = tempfile.mkdtemp(prefix="spreads.")
        split_config = self._split_configuration(projectfile, temp_dir)
        logger.debug("Launching those subprocesses!")
        processes = [subprocess.Popen(['scantailor-cli', '--start-filter=6',
                                       x, out_dir])
                     for x in split_config]
        while processes:
            for p in processes[:]:
                if p.poll() is not None:
                    processes.remove(p)
        shutil.rmtree(temp_dir)

    def process(self, path):
        autopilot = (self.config['scantailor']['autopilot']
                     .get(bool) or self.config['autopilot'].get(bool))
        if not autopilot and not find_in_path('scantailor'):
            raise MissingDependencyException(
                "Could not find executable `scantailor` in"
                " $PATH. Please install the appropriate"
                " package(s)!")
        projectfile = os.path.join(path, "{0}.ScanTailor".format(
            os.path.basename(path)))
        img_dir = os.path.join(path, 'raw')
        out_dir = os.path.join(path, 'done')

        if not os.path.exists(projectfile):
            self._generate_configuration(projectfile, img_dir, out_dir)
        if not autopilot:
            logger.info("Opening ScanTailor GUI for manual adjustment")
            subprocess.call(['scantailor', projectfile])
        logger.info("Generating output images from ScanTailor configuration.")
        self._generate_output(projectfile, out_dir)

# -*- coding: utf-8 -*-

from __future__ import division, unicode_literals

import logging
import math
import multiprocessing
import re
import shutil
import subprocess
import tempfile
from xml.etree.cElementTree import ElementTree as ET

from spreads.vendor.pathlib import Path

from spreads.plugin import HookPlugin, PluginOption
from spreads.util import find_in_path, MissingDependencyException

if not find_in_path('scantailor-cli'):
    raise MissingDependencyException("Could not find executable"
                                     " `scantailor-cli` in $PATH. Please"
                                     " install the appropriate package(s)!")

logger = logging.getLogger('spreadsplug.scantailor')


class ScanTailorPlugin(HookPlugin):
    __name__ = 'scantailor'

    _enhanced = bool(re.match(r".*<images\|directory\|->.*",
                              subprocess.check_output('scantailor-cli')
                              .splitlines()[7]))

    @classmethod
    def configuration_template(cls):
        conf = {'autopilot': PluginOption(value=False,
                                          docstring="Skip manual correction"),
                'rotate': PluginOption(value=False, docstring="Rotate pages"),
                'split_pages': PluginOption(value=True,
                                            docstring="Split pages"),
                'deskew': PluginOption(value=True, docstring="Deskew pages"),
                'content': PluginOption(value=True,
                                        docstring="Detect page content"),
                'auto_margins': PluginOption(value=True,
                                             docstring="Automatically detect"
                                                       " margins"),
                'detection': PluginOption(value=('content', 'page'),
                                          docstring="Content detection mode",
                                          selectable=True),
                'margins': PluginOption([2.5, 2.5, 2.5, 2.5])
                }
        return conf

    def _generate_configuration(self, projectfile, img_dir, out_dir):
        if not out_dir.exists():
            out_dir.mkdir()
        logger.info("Generating ScanTailor configuration")
        filterconf = [self.config[x].get(bool)
                      for x in ('rotate', 'split_pages', 'deskew', 'content',
                                'auto_margins')]
        start_filter = filterconf.index(True)+1
        end_filter = len(filterconf) - list(reversed(filterconf)).index(True)+1
        marginconf = self.config['margins'].as_str_seq()
        generation_cmd = ['scantailor-cli',
                          '--start-filter={0}'.format(start_filter),
                          '--end-filter={0}'.format(end_filter),
                          '--layout=1.5',
                          '-o={0}'.format(projectfile)]
        page_detection = self.config['detection'].get() == 'page'
        if self._enhanced and page_detection:
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
        if self._enhanced:
            generation_cmd.append(unicode(img_dir))
        else:
            generation_cmd.extend([unicode(x)
                                   for x in sorted(img_dir.iterdir())])
        generation_cmd.append(unicode(out_dir))
        logger.debug(" ".join(generation_cmd))
        subprocess.call(generation_cmd)

    def _split_configuration(self, projectfile, temp_dir):
        num_pieces = multiprocessing.cpu_count()
        tree = ET(file=unicode(projectfile))
        num_files = len(tree.findall('./files/file'))
        splitfiles = []
        files_per_job = int(math.ceil(float(num_files)/num_pieces))
        for idx in xrange(num_pieces):
            tree = ET(file=unicode(projectfile))
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
            out_file = temp_dir / "{0}-{1}.ScanTailor".format(projectfile.stem,
                                                              idx)
            tree.write(unicode(out_file))
            splitfiles.append(out_file)
        return splitfiles

    def _generate_output(self, projectfile, out_dir):
        logger.debug("Generating output...")
        temp_dir = Path(tempfile.mkdtemp(prefix="spreads."))
        split_config = self._split_configuration(projectfile, temp_dir)
        logger.debug("Launching those subprocesses!")
        processes = [subprocess.Popen(['scantailor-cli', '--start-filter=6',
                                       unicode(cfgfile), unicode(out_dir)])
                     for cfgfile in split_config]
        while processes:
            for p in processes[:]:
                if p.poll() is not None:
                    processes.remove(p)
        shutil.rmtree(unicode(temp_dir))

    def process(self, path):
        autopilot = self.config['autopilot'].get(bool)
        if not autopilot and not find_in_path('scantailor'):
            raise MissingDependencyException(
                "Could not find executable `scantailor` in"
                " $PATH. Please install the appropriate"
                " package(s)!")
        projectfile = path / "{0}.ScanTailor".format(path.name)
        img_dir = path / 'raw'
        out_dir = path / 'done'

        if not projectfile.exists():
            self._generate_configuration(projectfile, img_dir, out_dir)
        if not autopilot:
            logger.info("Opening ScanTailor GUI for manual adjustment")
            subprocess.call(['scantailor', unicode(projectfile)])
        logger.info("Generating output images from ScanTailor configuration.")
        self._generate_output(projectfile, out_dir)

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

from __future__ import division, unicode_literals

import logging
import math
import multiprocessing
import platform
import re
import shutil
import subprocess
import tempfile
import time
from xml.etree.cElementTree import ElementTree as ET

import psutil
from spreads.vendor.pathlib import Path

from spreads.config import OptionTemplate
from spreads.plugin import HookPlugin, ProcessHookMixin
from spreads.util import (find_in_path, MissingDependencyException,
                          SpreadsException, wildcardify)

if not find_in_path('scantailor-cli'):
    raise MissingDependencyException("Could not find executable"
                                     " `scantailor-cli`. Please" " install the"
                                     " appropriate package(s)!")

IS_WIN = platform.system() == 'Windows'

logger = logging.getLogger('spreadsplug.scantailor')


class ScanTailorPlugin(HookPlugin, ProcessHookMixin):
    __name__ = 'scantailor'

    @classmethod
    def configuration_template(cls):
        conf = {
            'autopilot': OptionTemplate(value=True,
                                        docstring="Skip manual correction"),
            'rotate': OptionTemplate(value=False, docstring="Rotate pages"),
            'split_pages': OptionTemplate(value=True,
                                          docstring="Split pages"),
            'deskew': OptionTemplate(value=True, docstring="Deskew pages"),
            'content': OptionTemplate(value=True,
                                      docstring="Detect page content"),
            'auto_margins': OptionTemplate(value=True,
                                           docstring="Automatically detect"
                                                     " margins"),
            'detection': OptionTemplate(value=('content', 'page'),
                                        docstring="Content detection mode",
                                        selectable=True),
            'margins': OptionTemplate([2.5, 2.5, 2.5, 2.5])
        }
        return conf

    def __init__(self, config):
        super(ScanTailorPlugin, self).__init__(config)
        self._enhanced = bool(re.match(r".*<images\|directory\|->.*",
                              subprocess.check_output(
                                  find_in_path('scantailor-cli'))
                              .splitlines()[7]))

    def _generate_configuration(self, in_paths, projectfile, out_dir):
        filterconf = [self.config[x].get(bool)
                      for x in ('rotate', 'split_pages', 'deskew', 'content',
                                'auto_margins')]
        start_filter = filterconf.index(True)+1
        end_filter = len(filterconf) - list(reversed(filterconf)).index(True)
        marginconf = self.config['margins'].as_str_seq()
        generation_cmd = [find_in_path('scantailor-cli'),
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
        # NOTE: We cannot pass individual filenames on windows, since we have
        # a limit of 32,768 characters for commands. Thus, we first try to
        # find a wildcard for our paths that matches only them, and if that
        # fails, throw an Exception and tell the user to use a proper OS...
        wildcard = wildcardify(in_paths)
        if not wildcard and IS_WIN:
            raise SpreadsException("Please use a proper operating system.")
        elif not wildcard:
            generation_cmd.extend(in_paths)
        else:
            generation_cmd.append(wildcard)

        generation_cmd.append(unicode(out_dir))
        logger.debug(" ".join(generation_cmd))
        proc = psutil.Process(subprocess.Popen(generation_cmd).pid)

        num_images = len(in_paths)
        num_steps = (end_filter - start_filter)+1
        last_fileidx = 0
        recent_fileidx = 0
        finished_steps = 0
        while proc.is_running():
            try:
                recent_fileidx = next(in_paths.index(x.path)
                                      for x in proc.open_files()
                                      if x.path in in_paths)
            except StopIteration:
                pass
            except psutil.AccessDenied:
                # This means the process is no longer running
                break
            if recent_fileidx == last_fileidx:
                time.sleep(.01)
                continue
            if recent_fileidx < last_fileidx:
                finished_steps += 1
            last_fileidx = recent_fileidx
            progress = 0.5*((finished_steps*num_images+last_fileidx) /
                            float(num_steps*num_images))
            self.on_progressed.send(self, progress=progress)

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

    def _generate_output(self, projectfile, out_dir, num_pages):
        logger.debug("Generating output...")
        temp_dir = Path(tempfile.mkdtemp(prefix="spreads."))
        split_config = self._split_configuration(projectfile, temp_dir)
        logger.debug("Launching those subprocesses!")
        processes = [subprocess.Popen([find_in_path('scantailor-cli'),
                                       '--start-filter=6', unicode(cfgfile),
                                       unicode(out_dir)])
                     for cfgfile in split_config]

        last_count = 0
        while processes:
            recent_count = sum(1 for x in out_dir.glob('*.tif'))
            if recent_count > last_count:
                progress = 0.5 + (float(recent_count)/num_pages)/2
                self.on_progressed.send(self, progress=progress)
                last_count = recent_count
            for p in processes[:]:
                if p.poll() is not None:
                    processes.remove(p)
            time.sleep(.01)
        shutil.rmtree(unicode(temp_dir))

    def process(self, pages, target_path):
        autopilot = self.config['autopilot'].get(bool)
        if not autopilot and not find_in_path('scantailor'):
            raise MissingDependencyException(
                "Could not find executable `scantailor` in"
                " $PATH. Please install the appropriate"
                " package(s)!")

        # Create temporary files/directories
        projectfile = Path(tempfile.mkstemp(suffix='.ScanTailor')[1])
        out_dir = Path(tempfile.mkdtemp(prefix='st-out'))

        # Map input paths to their pages so we can more easily associate
        # the generated output files with their pages later on
        in_paths = {}
        for page in pages:
            fpath = page.get_latest_processed(image_only=True)
            if fpath is None:
                fpath = page.raw_image
            in_paths[unicode(fpath)] = page

        logger.info("Generating ScanTailor configuration")
        self._generate_configuration(sorted(in_paths.keys()),
                                     projectfile, out_dir)

        if not autopilot:
            logger.warn("If you are changing output settings (in the last "
                        "step, you *have* to run the last step from the GUI. "
                        "Due to a bug in ScanTailor, your settings would "
                        "otherwise be ignored.")
            time.sleep(5)
            logger.info("Opening ScanTailor GUI for manual adjustment")
            subprocess.call([find_in_path('scantailor'), unicode(projectfile)])
        # Check if the user already generated output files from the GUI
        if not sum(1 for x in out_dir.glob('*.tif')) == len(pages):
            logger.info("Generating output images from ScanTailor "
                        "configuration.")
            self._generate_output(projectfile, out_dir, len(pages))

        # Associate generated output files with our pages
        for fname in out_dir.glob('*.tif'):
            out_stem = fname.stem
            for in_path, page in in_paths.iteritems():
                if Path(in_path).stem == out_stem:
                    target_fname = target_path/fname.name
                    shutil.copyfile(unicode(fname), unicode(target_fname))
                    page.processed_images[self.__name__] = target_fname
                    break
            else:
                logger.warn("Could not find page for output file {0}"
                            .format(fname))

        # Remove temporary files/directories
        shutil.rmtree(unicode(out_dir))
        projectfile.unlink()

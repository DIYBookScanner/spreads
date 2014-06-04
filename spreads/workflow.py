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

"""
spreads workflow object.
"""

from __future__ import division, unicode_literals

import logging
import multiprocessing
import shutil
import threading
import uuid
from datetime import datetime

import spreads.vendor.bagit as bagit
import spreads.vendor.confit as confit
from blinker import Namespace
from concurrent.futures import ThreadPoolExecutor
from spreads.vendor.pathlib import Path

import spreads.plugin as plugin
from spreads.config import Configuration
from spreads.util import (check_futures_exceptions, get_free_space, slugify,
                          DeviceException, SpreadsException)

# TODO: Example status dict:
# {
#   'step': 'process',
#   'step_progress': 0.5,
#   'prepared': True,
# }

signals = Namespace()
on_created = signals.signal(
    'workflow:created',
    doc="Sent by a :class:`Workflow` when a new workflow was created.")

on_step_progressed = signals.signal('workflow:progressed', doc="""\
Sent by a :class:`Workflow` after it has made progress on a running step
like 'postprocess' or 'output'.

:argument :class:`Workflow`:      the Workflow that has made progress
:keyword unicode step:            the name of the currently active step
:keyword unicode plugin:          the name of the currently running plugin
:keyword float progress:          the progress of the current step as a
                                  value between 0 and 1.
""")

on_status_updated = signals.signal('workflow:status_updated', doc="""\
Sent by a :class:`Workflow` after its status has changed.

:argument :class:`Workflow`:      the Workflow that has made progress
:keyword dict status:             the updated status
""")

on_config_updated = signals.signal('workflow:config_updated', doc="""\
Sent by a :class:`Workflow` after modifications to its configuration were
made.

:argument :class:`Workflow`:  the Workflow whose configuration was modified
:keyword dict changes:        the changed configuration items.
""")

on_removed = signals.signal('workflow:removed', doc="""\
Sent by the removing code when a workflow was deleted.

:keyword unicode id: the ID of the :class:`Workflow` that was removed
""")

on_capture_triggered = signals.signal('workflow:capture-triggered', doc="""\
Sent by a :class:`Workflow` after a capture was triggered.

:argument :class:`Workflow`:  the Workflow a capture was triggered on
""")

on_capture_succeeded = signals.signal('workflow:capture-succeeded', doc="""\
Sent by a :class:`Workflow` after a capture was successfully executed.

:argument :class:`Workflow`:  the Workflow a capture was executed on
:keyword list<Path> images:          the images that were captured
:keyword bool retake          whether the shot was a retake
""")


class ValidationError(Exception):
    def __init__(self, **kwargs):
        self.errors = kwargs

on_created.connect(lambda sender: Workflow._add_to_cache(sender))


class Workflow(object):
    _cache = {}

    @classmethod
    def create(cls, location, name, config=None):
        if not isinstance(location, Path):
            location = Path(location)
        if (location/name).exists():
            raise ValidationError(
                name="A workflow with that name already exists")
        wf = cls(path=location/name, config=config)
        if not location in cls._cache:
            cls._cache[location] = []
        cls._cache[location].append(wf)
        return wf

    @classmethod
    def _add_to_cache(cls, workflow):
        location = workflow.path.parent
        if not location in cls._cache:
            return
        if not workflow in Workflow._cache[location]:
            cls._cache[location] = workflow

    @classmethod
    def find_all(cls, location, key='slug', reload=False):
        """ List all workflows in the given location.

        :param location:    Location where the workflows are located
        :type location:     unicode/pathlib.Path
        """
        if not isinstance(location, Path):
            location = Path(location)
        if key not in ('slug', 'id'):
            raise ValueError("'key' must be one of ('id', 'slug')")
        if location in cls._cache and not reload:
            found = cls._cache[location]
        else:
            found = []
            for candidate in location.iterdir():
                is_workflow = ((candidate/'bagit.txt').exists
                               or (candidate/'raw').exists)
                if not is_workflow:
                    continue
                workflow = cls(candidate)
                found.append(workflow)
            cls._cache[location] = found
        return {getattr(wf, key): wf for wf in cls._cache[location]}

    @classmethod
    def find_by_id(cls, location, id):
        if not isinstance(location, Path):
            location = Path(location)
        try:
            return cls.find_all(location, key='id')[id]
        except KeyError:
            return None

    @classmethod
    def find_by_slug(cls, location, slug):
        if not isinstance(location, Path):
            location = Path(location)
        try:
            return cls.find_all(location, key='slug')[slug]
        except KeyError:
            return None

    @classmethod
    def remove(cls, workflow):
        if workflow.status['step'] is not None:
            raise SpreadsException(
                "Cannot remove a workflow while it is busy."
                " (active step: '{0}')".format(workflow.status['step']))
        shutil.rmtree(unicode(workflow.path))
        cls._cache[workflow.path.parent].remove(workflow)
        on_removed.send(id=workflow.id)

    def __init__(self, path, config=None):
        self._logger = logging.getLogger('Workflow')
        self._logger.debug("Initializing workflow {0}".format(path))
        self.status = {
            'step': None,
            'step_progress': None,
            'prepared': False
        }
        if not isinstance(path, Path):
            path = Path(path)
        self.path = path
        is_new = not self.path.exists()
        try:
            self.bag = bagit.Bag(unicode(self.path))
        except bagit.BagError:
            # Convert non-bagit directories from older versions
            self.bag = bagit.Bag.convert_directory(unicode(self.path))
        if not self.slug:
            self.slug = slugify(unicode(self.path.name))
        if not self.id:
            self.id = unicode(uuid.uuid4())
        # See if supplied `config` is already a valid ConfigView object
        if isinstance(config, confit.ConfigView):
            self.config = config
        elif isinstance(config, Configuration):
            self.config = config.as_view()
        else:
            self.config = self._load_config(config)
        self._capture_lock = threading.RLock()
        self._devices = None
        self._pluginmanager = None
        self._pool_executor = None

        if is_new:
            on_created.send(self)

        # Filter out subcommand plugins, since these are not workflow-specific
        plugin_classes = [
            (name, cls)
            for name, cls in plugin.get_plugins(*self.config["plugins"]
                                                .get()).iteritems()
            if not cls.__bases__ == (plugin.SubcommandHookMixin,)]
        self.plugins = [cls(self.config) for name, cls in plugin_classes]
        self.config['plugins'] = [name for name, cls in plugin_classes]

        # Save configuration
        self.save_config()

        # Update status when a step has progressed
        on_step_progressed.connect(
            lambda _, __, progress: self.update_status('step_progressed',
                                                       progress),
            sender=self)

    @property
    def id(self):
        return self.bag.info.get('spreads-id')

    @id.setter
    def id(self, value):
        self.bag.info['spreads-id'] = value

    @property
    def slug(self):
        return self.bag.info.get('spreads-slug')

    @slug.setter
    def slug(self, value):
        # TODO: Check to avoid duplicates
        self.bag.info['spreads-slug'] = value

    @property
    def last_modified(self):
        return datetime.fromtimestamp(
            max(Path(self.path/fname).stat().st_mtime
                for fname in ('manifest-md5.txt', 'tagmanifest-md5.txt')))

    @property
    def devices(self):
        if 'driver' not in self.config.keys():
            raise DeviceException(
                "No driver has been configured\n"
                "Please run `spread configure` to select a driver.")
        if self._devices is None:
            self._devices = plugin.get_devices(self.config, force_reload=True)
        if any(not dev.connected() for dev in self._devices):
            self._logger.warning(
                "At least one of the devices has been disconnected."
                "Please make sure it has been re-enabled before taking another"
                "action.")
            self._devices = None
        if not self._devices:
            raise DeviceException("Could not find any compatible devices!")
        return self._devices

    @property
    def images(self):
        # NOTE: We are not using the bag for this, since we hash files
        #       asynchronously and it takes some time for the files to
        #       land in the bag.
        raw_path = self.path / 'data' / 'raw'
        if not raw_path.exists():
            return []
        return sorted(raw_path.iterdir())

    @property
    def out_files(self):
        # NOTE: Not using the bag here either, check :ref:`images` for
        #       details
        out_path = self.path / 'data' / 'out'
        if not out_path.exists():
            return []
        else:
            return sorted(out_path.iterdir())

    def _update_status(self, key, value):
        self.status[key] = value
        on_status_updated.send(self, status=self.status)

    def _load_config(self, value):
        # Load default configuration
        config = Configuration()
        cfg_file = self.path / 'config.yml'
        if value is None and cfg_file.exists():
            # Load workflow-specific configuration from file
            value = confit.ConfigSource({}, unicode(cfg_file))
        if value is not None:
            # Load configuration from supplied ConfigSource or dictionary
            config = config.with_overlay(value)
        return config

    def save_config(self):
        cfg_path = self.path/'config.yaml'
        self.config.dump(
            unicode(cfg_path), True,
            self.config["plugins"].get() + ["plugins", "device"])
        self.bag.add_tagfiles(unicode(cfg_path))

    def _run_hook(self, hook_name, *args):
        self._logger.debug("Running '{0}' hooks".format(hook_name))
        plugins = [x for x in self.plugins if hasattr(x, hook_name)]
        for (idx, plug) in enumerate(plugins):
            plug.on_progressed.connect(
                lambda sender, **kwargs: on_step_progressed.send(
                    self, plugin_name=sender.__name__,
                    progress=(float(idx)/len(plugins) +
                              kwargs['progress']*1.0/len(plugins))),
                sender=plug, weak=False
            )
            getattr(plug, hook_name)(*args)
            on_step_progressed.send(self, plugin_name=plug.__name__,
                                    progress=float(idx+1)/len(plugins))

    def _get_next_filename(self, target_page=None):
        """ Get next filename that a capture should be stored as.

        If the workflow is shooting with two devices, this will select a
        filename that matches the device's target page (odd/even).

        :param target_page: target page of file ('odd/even')
        :type target_page:  str/unicode/None if not applicable
        :return:            absolute path to next filename
                            (e.g. /tmp/proj/003.jpg)
        :rtype:             pathlib.Path
        """
        base_path = self.path / 'data' / 'raw'
        if not base_path.exists():
            base_path.mkdir()

        try:
            last_num = int(self.images[-1].stem)
        except IndexError:
            last_num = -1

        if target_page is None:
            return base_path / "{03:0}".format(last_num+1)

        next_num = (last_num+2 if target_page == 'odd' else last_num+1)
        return base_path / "{0:03}".format(next_num)

    def prepare_capture(self):
        self._logger.info("Preparing capture.")
        self._update_status('step', 'capture')
        self._pool_executor = ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count())
        if any(dev.target_page is None for dev in self.devices):
            raise DeviceException(
                "Target page for at least one of the devicescould not be"
                "determined, please run 'spread configure' to configure your"
                "your devices.")
        with ThreadPoolExecutor(len(self.devices)) as executor:
            futures = []
            self._logger.debug("Preparing capture in devices")
            for dev in self.devices:
                futures.append(executor.submit(dev.prepare_capture, self.path))
        check_futures_exceptions(futures)

        flip_target = ('flip_target_pages' in self.config['device'].keys()
                       and self.config['device']['flip_target_pages'].get())
        if flip_target:
            (self.devices[0].target_page,
             self.devices[1].target_page) = (self.devices[1].target_page,
                                             self.devices[0].target_page)
        self._run_hook('prepare_capture', self.devices, self.path)
        self._run_hook('start_trigger_loop', self.capture)
        self._update_status('prepared', True)

    def capture(self, retake=False):
        if not self.status['prepared']:
            raise SpreadsException("Capture was not prepared before.")
        with self._capture_lock:
            self._logger.info("Triggering capture.")
            on_capture_triggered.send(self)
            parallel_capture = (
                'parallel_capture' in self.config['device'].keys()
                and self.config['device']['parallel_capture'].get()
            )
            num_devices = len(self.devices)

            # Abort when there is little free space
            if get_free_space(self.path) < 50*(1024**2):
                raise IOError("Insufficient disk space to take a capture.")

            if retake:
                # Remove last n images, where n == len(self.devices)
                map(lambda x: x.unlink(), self.images[-num_devices:])

            futures = []
            with ThreadPoolExecutor(num_devices
                                    if parallel_capture else 1) as executor:
                self._logger.debug("Sending capture command to devices")
                for dev in self.devices:
                    img_path = self._get_next_filename(dev.target_page)
                    futures.append(executor.submit(dev.capture, img_path))
            check_futures_exceptions(futures)

            self._run_hook('capture', self.devices, self.path)
            # Queue new images for hashing
            self._pool_executor.submit(
                self.bag.add_payload,
                *(unicode(x) for x in self.images[-num_devices:]))
        on_capture_succeeded.send(self, images=self.images[-num_devices:],
                                  retake=retake)

    def finish_capture(self):
        if self._pool_executor:
            self._pool_executor.shutdown(wait=False)
            self._pool_executor = None
        with ThreadPoolExecutor(len(self.devices)) as executor:
            futures = []
            self._logger.debug("Sending finish_capture command to devices")
            for dev in self.devices:
                futures.append(executor.submit(dev.finish_capture))
        check_futures_exceptions(futures)
        self._run_hook('finish_capture', self.devices, self.path)
        self._run_hook('stop_trigger_loop')
        self._update_status('step', None)
        self._update_status('prepared', False)

    def process(self):
        self._update_status('step', 'process')
        self._logger.info("Starting postprocessing...")
        self._run_hook('process', self.path)
        self.bag.add_payload(str(self.path/'data'/'done'))
        self._logger.info("Done with postprocessing!")
        self._update_status('step', None)

    def output(self):
        self._logger.info("Generating output files...")
        self._update_status('step', 'output')
        out_path = self.path / 'data' / 'out'
        if not out_path.exists():
            out_path.mkdir()
        self._run_hook('output', self.path)
        self.bag.add_payload(str(out_path))
        self._logger.info("Done generating output files!")
        self._update_status('step', None)

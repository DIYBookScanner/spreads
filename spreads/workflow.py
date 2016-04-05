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
Central :py:class:`Workflow` entity (and its signals) and various associated
entities.
"""

from __future__ import division, unicode_literals

import copy
import logging
import shutil
import threading
import uuid
from datetime import datetime

import concurrent.futures as concfut
import spreads.vendor.bagit as bagit
import spreads.vendor.confit as confit
import json
from blinker import Namespace
from pathlib import Path

import spreads.plugin as plugin
import spreads.util as util
from spreads.config import Configuration
from spreads.metadata import Metadata

try:
    from jpegtran import JPEGImage
    HAS_JPEGTRAN = True
except ImportError:
    HAS_JPEGTRAN = False
    from PIL import Image

signals = Namespace()
on_created = signals.signal('workflow:created', doc="""\
Sent by a :class:`Workflow` when a new workflow was created.

:argument :class:`Workflow`:    the newly created Workflow
""")

on_modified = signals.signal('workflow:modified', doc="""\
Sent by a :class:`Workflow` when it was modified.

:argument class:`Workflow`:     the workflow that was modified
:keyword  dict changes          the modified attributes
""")

on_removed = signals.signal('workflow:removed', doc="""\
Sent by the removing code when a workflow was deleted.

:keyword unicode senderId: the ID of the :class:`Workflow` that was removed
""")

on_capture_triggered = signals.signal('workflow:capture-triggered', doc="""\
Sent by a :class:`Workflow` after a capture was triggered.

:argument :class:`Workflow`:  the Workflow a capture was triggered on
""")

on_capture_succeeded = signals.signal('workflow:capture-succeeded', doc="""\
Sent by a :class:`Workflow` after a capture was successfully executed.

:argument :class:`Workflow`:  the Workflow a capture was executed on
:keyword list<Path> pages:    the pages that were captured
:keyword bool retake          whether the shot was a retake
""")

on_capture_failed = signals.signal('workflow:capture-failed', doc="""\
Sent by a :class:`Workflow` after a capture failed.

:argument :class:`Workflow`:    the Workflow the capture failed for
:keyword unicode message:       A message that explains the cause of the
                                failure
""")


def _signal_on_error(signal):
    """ Decorator for emitting a signal when a function throws an exception.

    :param signal:      The signal to emit when an exception is thrown
                        Should take the exception as its sole argument
    :type signal:       blinker.Signal
    """
    def wrap(func):
        def wrapped_func(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                signal.send(args[0],  # self
                            message=e.message)
                raise
        return wrapped_func
    return wrap


class ValidationError(ValueError):
    """ Raised when some kind of validation error occured.

    :attr message:  General error message
    :attr errors:   Mapping from field name to validation error message
    """
    def __init__(self, message=None, **kwargs):
        """ Create new instance.

        ``**kwargs`` should be a mapping from a field name to an error
        message.
        """
        if message is None:
            message = "Invalid values for {0}".format(kwargs.keys())
        super(ValueError, self).__init__(message)
        self.errors = kwargs


class Page(object):
    """ Entity that holds information about a single page.

    :attr raw_image:        The path to the raw image.
    :attr processed_images: A dictionary of plugin names mapped to the path of
                            a processed file.
    :attr capture_num:      The capture number of the page, i.e. at what
                            position in the workflow it was recorded, including
                            aborted and retaken shots.
    :attr sequence_num:     The sequence number of the page, i.e. at what
                            position in the list of 'good' captures it is.
                            Usually identical with the position in the
                            containing `pages` list. Defaults to the capture
                            number.
    :attr page_label:       A label for the page. Must be an integer, a string
                            of digits or a roman numeral (e.g. 12, '12',
                            'XII'). Defaults to the sequence number.
    """
    # FIXME: This type is insufficient for the case where the raw images
    # contain two individual pages, i.e. the whole bookspreads was captured in
    # a single image. How would we deal with that scenario?
    __slots__ = ["sequence_num", "capture_num", "raw_image", "page_label",
                 "processed_images"]

    def __init__(self, raw_image, sequence_num=None, capture_num=None,
                 page_label=None, processed_images=None):
        self.raw_image = raw_image
        self.processed_images = processed_images or {}
        if capture_num:
            self.capture_num = capture_num
        else:
            self.capture_num = int(raw_image.stem)
        self.sequence_num = sequence_num or self.capture_num
        if page_label:
            # TODO: Add support for letter numbering (e.g. 'a' -> 1,
            #       'aa' -> 27, 'zz' -> 52, etc)
            # TODO: Add support for prefixes (e.g. 'A-1')
            valid_string = (isinstance(page_label, basestring) and
                            (page_label.isdigit() or
                             util.RomanNumeral.is_roman(page_label.upper())))
            if not isinstance(page_label, int) and not valid_string:
                raise ValidationError(
                    page_label=("Must be an integer, a string of digits, a "
                                "roman numeral string or a RomanNumeral "
                                "type"))
            self.page_label = str(page_label)
        else:
            self.page_label = unicode(self.sequence_num)

    def get_latest_processed(self, image_only=True):
        """ Get the least recent postprocessed file

        :param image_only:  Only return image files (e.g. no OCR files)
        :type image_only:   bool
        :returns:           Path to least recent postprocessed file
        :rtype:             :py:class:`pathlib.Path`
        """
        img_exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
        paths = self.processed_images.values()
        if image_only:
            paths = [p for p in paths if p.suffix.lower() in img_exts]
        try:
            return sorted(paths,
                          key=lambda p: p.stat().st_mtime, reverse=True)[0]
        except IndexError:
            return None

    def to_dict(self):
        """ Serialize entity to a dict.

        Used by :py:class:`spreads.util.CustomJSONEncoder`.
        """
        return {
            'sequence_num': self.sequence_num,
            'capture_num': self.capture_num,
            'page_label': self.page_label,
            'raw_image': self.raw_image,
            'processed_images': self.processed_images,
        }


class TocEntry(object):
    """ Represent a 'table of contents' entry.

    :attr title:        Label/title of the entry
    :attr start_page:   First page of the entry
    :attr end_page:     First page no longer part of the entry
    :attr children;     Other :py:class:`TocEntry` objects that designate a
                        sub-range of this entry
    """
    __slots__ = ("title", "start_page", "end_page", "children")

    def __init__(self, title, start_page, end_page, children=None):
        self.title = title
        self.start_page = start_page
        self.end_page = end_page
        self.children = children

    def __repr__(self):
        return (
            u"TocEntry(title={0}, start_page={1}, end_page={2}, "
            u"children={3})"
        ).format(repr(self.title), repr(self.start_page), repr(self.end_page),
                 repr(self.children))

    def to_dict(self):
        """ Serialize entity to a dict.

        Used by :py:class:`spreads.util.CustomJSONEncoder`.
        """
        return {
            'title': self.title,
            'start_page': self.start_page.sequence_num,
            'end_page': self.end_page.sequence_num,
            'children': self.children
        }


class Workflow(object):
    """ Core entity for managing scanning workflows.

    :attr id:           UUID for the workflow
    :attr status:       Current status. Keys are ``step`` ('capture', 'process'
                        or 'output'), ``step_progress`` (Progress as a value
                        between 0 and 1) and ``prepared`` (whether capture is
                        already prepared).
    :type status:       dict
    :attr path:         Path to directory containing the
                        workflow's data.
    :type path;         :py:class:`pathlib.Path`
    :attr bag:          Underlying  BagIt data structure
    :type bag:          py:class:`spreads.vendor.bagit.Bag`
    :attr slug:         ASCIIfied version of workflow title without spaces.
    :attr config:       Configuration for the worklfow, takes precedence
                        over the global configuration).
    :type config:       py:class:`confit.ConfigView`
    :attr metadata:     Metadata, contains at least a ``title`` field.
    :type metadata:     :py:class:`spreads.metadata.Metadata`
    :attr pages:        Pages available in the workflow
    :type pages:        list of :py:class:`Page`
    :attr table_of_contents: Table of contents entries in the workflow
    :type table_of_contents: list of :py:class:`TocEntry`
    :attr last_modified: Time of last modification
    :type last_modified: py:class:`datetime.datetime`
    :attr devices:      Active devices
    :type devices:      list of py:class:`spreads.plugin.DeviceDriver`
    :attr out_files:    Generated output files
    :type out_files:    list of :py:class:`pathlib.Path`
    """
    # Class-wide cache of :py:class:`Workflow` instances
    _cache = {}

    def __new__(cls, *args, **kwargs):
        """ Automatically cache every new :py:class:`Workflow` instance. """
        on_created.connect(lambda sender, **kwargs: cls._add_to_cache(sender),
                           weak=False)
        return super(Workflow, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def create(cls, location, metadata=None, config=None):
        """ Create a new Workflow.

        :param location:    Base directory that the workflow should be created
                            in
        :type location:     unicode or :py:class:`pathlib.Path`
        :param metadata:    Initial metadata for workflow. Must at least
                            contain a `title` item.
        :type metadata:     dict
        :param config:      Initial configuration for workflow
        :type config:       dict or :py:class:`spreads.config.Configuration`
        :return:            The new instance
        :rtype:             :py:class:`Workflow`
        """
        if not isinstance(location, Path):
            location = Path(location)
        if metadata is None or 'title' not in metadata:
            raise ValidationError(
                metadata={'title': 'Please specify at least a title'})
        path = Path(location/util.slugify(metadata['title']))
        if path.exists():
            raise ValidationError(
                name="A workflow with that title already exists")
        wf = cls(path=path, config=config, metadata=metadata)
        return wf

    @classmethod
    def _add_to_cache(cls, workflow):
        location = workflow.path.parent
        if location not in cls._cache:
            cls._cache[location] = [workflow]
        elif workflow not in Workflow._cache[location]:
            cls._cache[location].append(workflow)

    @classmethod
    def find_all(cls, location, key='slug', reload=False):
        """ List all workflows in the given location.

        :param location:    Location where the workflows are located
        :type location:     unicode or :py:class:`pathlib.Path`
        :param key:         Attribute to use as key for returned dict
        :type key:          str/unicode
        :param reload:      Do not load workflows from cache
        :type reload:       bool
        :return:            All found workflows
        :rtype:             dict
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
            is_workflow = (location.is_dir() and
                           ((candidate/'bagit.txt').exists or
                            (candidate/'raw').exists))
            if not is_workflow:
                continue
            if not next((wf for wf in found if wf.path == candidate), None):
                logging.debug(
                    "Cache missed, instantiating workflow from {0}."
                    .format(candidate))
                try:
                    workflow = cls(candidate)
                except bagit.BagError as e:
                    logging.warn(e.message)
                    continue
                found.append(workflow)
        cls._cache[location] = found
        return {getattr(wf, key): wf for wf in cls._cache[location]}

    @classmethod
    def find_by_id(cls, location, id):
        """ Try to locate a workflow with the given id in a directory.

        :param location:    Base directory that contains workflows to be
                            searched among
        :type location:     unicode or :py:class:`pathlib.Path`
        :param id:          ID of workflow to be searched for
        :rtype:             :py:class:`Workflow` or None
        """
        if not isinstance(location, Path):
            location = Path(location)
        try:
            return cls.find_all(location, key='id')[id]
        except KeyError:
            return None

    @classmethod
    def find_by_slug(cls, location, slug):
        """ Try to locate a workflow that matches a given slug in a directory.

        :param location:    Base directory that contains workflows to be
                            searched among
        :type location:     unicode or :py:class:`pathlib.Path`
        :param slug:        Slug of workflow to be searched for
        :type slug:         unicode
        :rtype:             :py:class:`Workflow` or None
        """
        if not isinstance(location, Path):
            location = Path(location)
        try:
            return cls.find_all(location, key='slug')[slug]
        except KeyError:
            return None

    @classmethod
    def remove(cls, workflow):
        """ Delete a workflow from the disk and cache.

        :param workflow:    Workflow to be deleted
        :type workflow:     :py:class:`Workflow`
        """
        wf_busy = (workflow.status['step'] is not None and
                   workflow.status['step_progress'] < 1)
        if wf_busy:
            raise util.SpreadsException(
                "Cannot remove a workflow while it is busy."
                " (active step: '{0}')".format(workflow.status['step']))
        shutil.rmtree(unicode(workflow.path))
        cls._cache[workflow.path.parent].remove(workflow)
        on_removed.send(senderId=workflow.id)

    def __init__(self, path, config=None, metadata=None):
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

        # See if supplied `config` is already a valid ConfigView object
        if isinstance(config, confit.ConfigView):
            self.config = config
        elif isinstance(config, Configuration):
            self.config = config.as_view()
        else:
            self.config = self._load_config(config)

        try:
            self.bag = bagit.Bag(unicode(self.path))
        except bagit.BagError:
            if self.config['core']['convert_old'].get(bool):
                # Convert non-bagit directories from older versions
                self.bag = bagit.Bag.convert_directory(unicode(self.path))
                self.pages = [Page(img)
                              for img in (self.path/'data'/'raw').iterdir()]
                self._save_pages()
            else:
                raise bagit.BagError(
                    "Specified workflow directory is not structured according "
                    "to BagIt convertions and automatic conversion has been "
                    "disabled (check `convert_old` setting)")
        if not self.slug:
            self.slug = util.slugify(unicode(self.path.name))
        if not self.id:
            self.id = unicode(uuid.uuid4())
        #: :py:class:`spreads.metadata.Metadata` instance that backs the
        #: corresponding getter and setter
        self._metadata = Metadata(self.path)

        # This will invoke the setter
        if metadata:
            self.metadata = metadata

        #: Lock that is held when a shot is being executed during the capture
        #: phase
        self._capture_lock = threading.RLock()
        #: List of :py:class:`spreads.plugin.DeviceDriver` instances that
        #: backs the corresponding getters and setters
        self._devices = None
        # Thread pool for background tasks
        self._threadpool = concfut.ThreadPoolExecutor(max_workers=1)
        # List of unfinished :py:class:`concurrent.futures.Future` instances
        self._pending_tasks = []

        # Filter out subcommand plugins, since these are not workflow-specific
        plugin_classes = [
            (name, cls)
            for name, cls in plugin.get_plugins(*self.config["plugins"]
                                                .get()).iteritems()
            if not cls.__bases__ == (plugin.SubcommandHooksMixin,)]
        self._plugins = [cls(self.config) for name, cls in plugin_classes]
        self.config['plugins'] = [name for name, cls in plugin_classes]
        self._save_config()

        self.pages = self._load_pages()
        self.table_of_contents = self._load_toc()

        if is_new:
            on_created.send(self, workflow=self)

    @property
    def id(self):
        return self.bag.info.get('spreads-id')

    @id.setter
    def id(self, value):
        self.bag.info['spreads-id'] = value

    @property
    def slug(self):
        # Read from Bag info
        return self.bag.info.get('spreads-slug')

    @slug.setter
    def slug(self, value):
        # TODO: Check to avoid duplicates
        self.bag.info['spreads-slug'] = value

    @property
    def last_modified(self):
        # We use the most recent of the modified timestamps of the two
        # checksum files of the BagIt directory, since any relevant changes
        # to the workflow's structure will cause a change in at least one
        # file hash.
        return datetime.fromtimestamp(
            max(Path(self.path/fname).stat().st_mtime
                for fname in ('manifest-md5.txt', 'tagmanifest-md5.txt')))

    @property
    def devices(self):
        if 'driver' not in self.config.keys():
            raise util.DeviceException(
                "No driver has been configured\n"
                "Please run `spread configure` to select a driver.")
        if self._devices is None:
            self._devices = plugin.get_devices(self.config, force_reload=True)
        if any(not dev.connected() for dev in self._devices):
            self._logger.warning(
                "At least one of the devices has been disconnected. "
                "Please make sure it has been re-enabled before taking "
                "another action.")
            self._devices = None
        return self._devices

    @property
    def is_single_camera(self):
        return len(self.devices) == 1

    def _fix_page_numbers(self, page_to_remove):
        """ Fix page numbers and numeric page labels if a page was removed. """
        def get_num_type(num_str):
            if page_to_remove.page_label.isdigit():
                return int, None
            elif util.RomanNumeral.is_roman(page_to_remove.page_label):
                return util.RomanNumeral, page_to_remove.page_label.islower()
            elif num_str == '':
                return None, None

        # Fix page labels
        page_idx = self.pages.index(page_to_remove)
        num_type = get_num_type(page_to_remove.page_label)
        if num_type != (None, None):
            for next_page in self.pages[page_idx+1:]:
                if get_num_type(next_page.page_label) != num_type:
                    # We can stop re-numbering when the numbering scheme
                    # has changed
                    break
                num = num_type[0](next_page.page_label)
                next_page.page_label = str(num - 1)

        # Fix sequence numbers:
        # TODO: Verify....
        for idx, next_page in enumerate(self.pages[page_idx+1:], page_idx):
            next_page.sequence_num = idx

    def _fix_table_of_contents(self, page_to_remove):
        """ Fix table of contents if a page was removed. """
        def find_page_in_toc(toc):
            matches = []
            for entry in toc:
                if page_to_remove in (entry.start_page, entry.end_page):
                    matches.append(entry)
                if entry.children is not None:
                    matches.extend(find_page_in_toc(entry.children))
            return matches

        page_idx = self.pages.index(page_to_remove)
        for entry in find_page_in_toc(self.table_of_contents):
            if entry.start_page == page_to_remove:
                entry.start_page = self.pages[page_idx+1]
            else:
                entry.end_page = self.pages[page_idx-1]
        self._save_toc()

    def remove_pages(self, *pages):
        """ Remove one or more pages from the workflow.

        This will irrevocably remove the page metadata as well as all of its
        associated files, so use responsibly!

        :param pages:   One or more pages to remove
        :type pages:    :py:class:`Page`
        """
        for page in pages:
            page.raw_image.unlink()
            for fp in page.processed_images.itervalues():
                fp.unlink()
            self._fix_page_numbers(page)
            self._fix_table_of_contents(page)
            self.pages.remove(page)
        self._save_pages()
        self.bag.update_payload(fast=True)

    def crop_page(self, page, left, top, width=None, height=None, async=False):
        """ Crop a page's raw image.

        :param page:    Page the raw image of which should be cropped
        :param left:    X coordinate of crop boundary
        :param top:     Y coordinate of crop boundary
        :param width:   Width of crop box
        :param height:  Height of crop box
        :param async:   Perform the cropping in a background thread
        :return:        The Future object when ``async`` was ``True``
        :rtype:         :py:class:`concurrent.futures.Future`
        """
        # FIXME: Does this really have to be a Workflow method?
        def do_crop(fname, left, top, width, height):
            if HAS_JPEGTRAN:
                img = JPEGImage(fname)
            else:
                img = Image(filename=fname)
            width = (img.width - left) if width is None else width
            height = (img.height - top) if height is None else height
            if width > (img.width - left):
                width = img.width - left
            if height > (img.height - top):
                width = img.height - top
            if (left, top, width, height) == (0, 0, img.width, img.height):
                self._logger.warn("No-op crop parameters, skipping!")
                return
            self._logger.debug("Cropping \"{0}\" to x:{1} y:{2} w:{3} h:{4}"
                               .format(fname, left, top, width, height))
            try:
                cropped = img.crop(left, top, width=width, height=height)
                if HAS_JPEGTRAN:
                    cropped.save(fname)
                else:
                    img.save(filename=fname)
                    img.close()
            except Exception as e:
                self._logger.error("Cropping failed")
                self._logger.exception(e)

        fname = unicode(page.raw_image)
        if async:
            future = self._threadpool.submit(do_crop, fname, left, top, width,
                                             height)
            self._pending_tasks.append(future)
            return future
        else:
            do_crop(fname, left, top, width, height)

    @property
    def out_files(self):
        out_path = self.path / 'data' / 'out'
        if not out_path.exists():
            return []
        else:
            return sorted(out_path.iterdir())

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        # Empty old metadata
        for k in self._metadata:
            del self._metadata[k]
        # Save new metadata
        for k, v in value.items():
            self._metadata[k] = v
        on_modified.send(self, changes={'metadata': value})

    def save(self):
        """ Persist all changes to the corresponding files on disk. """
        self._save_config()
        self._save_toc()
        self._save_pages()

    def _update_status(self, **kwargs):
        """ Update :py:attr:`status` and emit a ``on_modified``  signal. """
        trigger_event = True
        if 'step_progress' in kwargs and kwargs['step_progress'] is not None:
            # Don't trigger event if we only made very little progress
            old_progress = self.status['step_progress']
            if old_progress is not None:
                prog_diff = kwargs['step_progress'] - old_progress
                trigger_event = (prog_diff >= 0.01 or   # Noticeable progress?
                                 prog_diff == -1 or     # New step?
                                 (old_progress < 1 and  # Completion?
                                     (old_progress + prog_diff) == 1))
                if not trigger_event:
                    kwargs.pop('step_progress', None)
        for key, value in kwargs.items():
            self.status[key] = value
        if trigger_event:
            # We really want to pass the status by value...
            on_modified.send(self, changes={'status': copy.copy(self.status)})

    def _load_config(self, value):
        """ Load configuartion from file in bag and optionally overlay it with
            new values.

        :param value:   Values to overlay over over loaded configuration
        :type value:    dict or :py:class:`confit.ConfigView`
        :returns:       Loaded (and overlaid) configuration
        :rtype:         :py:class:`confit.Configuration`
        """
        # Load default configuration
        config = Configuration()
        cfg_file = self.path / 'config.yml'
        if value is None and cfg_file.exists():
            # Load workflow-specific configuration from file
            value = confit.ConfigSource(confit.load_yaml(unicode(cfg_file)),
                                        unicode(cfg_file))
        if value is not None:
            # Load configuration from supplied ConfigSource or dictionary
            config = config.with_overlay(value)
        return config

    def _save_config(self):
        cfg_path = self.path/'config.yml'
        # Only save configuration from active plugins in addition to plugin
        # selection and device configuration
        self.config.dump(
            unicode(cfg_path), True,
            self.config["plugins"].get() + ["plugins", "device"])
        self.bag.add_tagfiles(unicode(cfg_path))

    def _load_toc(self, data=None):
        """ Load TOC entries from ``toc.json`` in bag or a passed list of
            dictionaries.

        :param data:    List of dictionaries to be deserialized
        :type data:     list of dict
        :rtype:         list of :py:class:`TocEntry`
        """
        def from_dict(dikt):
            start_page, end_page = None, None
            try:
                start_page = next(p for p in self.pages
                                  if p.sequence_num == dikt['start_page'])
                end_page = next(p for p in self.pages
                                if p.sequence_num == dikt['end_page'])
            except StopIteration:
                missing = 'end_page' if start_page else 'start_page'
                raise ValidationError(
                    *{missing: "No page with that sequence number."})
            children = [from_dict(x) for x in dikt['children']]
            return TocEntry(dikt['title'], start_page, end_page, children)

        if not data:
            toc_path = self.path / 'toc.json'
            if not toc_path.exists():
                return []
            with toc_path.open('r') as fp:
                data = json.load(fp)
        return [from_dict(e) for e in data]

    def _save_toc(self):
        """ Write TOC entries to ``toc.json`` in bag. """
        if not self.table_of_contents:
            return
        toc_path = self.path / 'toc.json'
        with toc_path.open('wb') as fp:
            json.dump([x.to_dict() for x in self.table_of_contents], fp,
                      cls=util.CustomJSONEncoder, indent=2, ensure_ascii=False)
        self.bag.add_tagfiles(unicode(toc_path))
        on_modified.send(self,
                         changes={'table_of_contents': self.table_of_contents})

    def _load_pages(self):
        """ Load pages from ``pagemeta.json`` in bag.

        :returns:   Deserialized pages
        :rtype:     list of :py:class:`Page`
        """
        def from_dict(dikt):
            raw_image = self.path/dikt['raw_image']
            processed_images = {}
            for plugname, fpath in dikt['processed_images'].iteritems():
                relpath = self.path/fpath
                if relpath.exists():
                    processed_images[plugname] = relpath
                else:
                    self._logger.warning(
                        "Could not find processed file {0}, removing from "
                        "workflow.".format(relpath))
            return Page(raw_image=raw_image,
                        capture_num=dikt['capture_num'],
                        processed_images=processed_images,
                        page_label=dikt['page_label'],
                        sequence_num=dikt['sequence_num'])
        fpath = self.path / 'pagemeta.json'
        if not fpath.exists():
            return []
        with fpath.open('r') as fp:
            return sorted([from_dict(p) for p in json.load(fp)],
                          key=lambda p: p.sequence_num)

    def _save_pages(self):
        """ Write pages to ``pagemeta.json`` in bag. """
        fpath = self.path / 'pagemeta.json'
        with fpath.open('wb') as fp:
            json.dump([x.to_dict() for x in self.pages], fp,
                      cls=util.CustomJSONEncoder, indent=2, ensure_ascii=False)
        self.bag.add_tagfiles(unicode(fpath))
        on_modified.send(self, changes={'pages': self.pages})

    def _run_hook(self, hook_name, *args):
        """ Run a specific hook method on all activated plugins.

        :param hook_name:   Name of hook method to run
        :param *args:       Arguments to pass to hook method
        """
        self._logger.debug("Running '{0}' hooks".format(hook_name))
        plugins = [x for x in self._plugins if hasattr(x, hook_name)]

        def update_progress(idx, plug_progress):
            """ Signal callback that updates the status and converts from
                per-plugin progress to per-workflow progress. """
            step_progress = float(idx) / len(plugins)
            internal_progress = plug_progress * (1.0 / len(plugins))
            self._update_status(
                step_progress=(step_progress + internal_progress))

        for (idx, plug) in enumerate(plugins):
            # FIXME: This should really be disconnected once we're done here
            plug.on_progressed.connect(
                lambda s, **kwargs: update_progress(idx, kwargs['progress']),
                sender=plug, weak=False)
            getattr(plug, hook_name)(*args)
            self._update_status(step_progress=float(idx+1)/len(plugins))

    def _get_next_capture_page(self, target_page=None):
        """ Get next page that a capture should be stored as.

        If the workflow is shooting with two devices, this will select a
        page with a sequence number that matches the device's target page
        (odd/even).

        :param target_page: target page of file ('odd/even')
        :type target_page:  str/unicode/None if not applicable
        :returns:           the target page object
        :rtype:             :py:class:`Page`
        """
        base_path = self.path / 'data' / 'raw'
        if not base_path.exists():
            base_path.mkdir()

        try:
            last_num = self.pages[-1].capture_num
        except IndexError:
            last_num = -1

        if target_page is None:
            return base_path / "{03:0}".format(last_num+1)

        is_raw = ('shoot_raw' in self.config['device'].keys() and
                  self.config['device']['shoot_raw'].get(bool))
        next_num = (last_num+1 if (self.is_single_camera or
                                   target_page == 'even')
                    else last_num+2)
        path = base_path / "{0:03}.{1}".format(next_num,
                                               'dng' if is_raw else 'jpg')
        return Page(path, capture_num=next_num)

    def prepare_capture(self):
        """ Prepare capture on devices and initialize trigger plugins. """
        self._logger.info("Preparing capture.")
        self._update_status(step='capture')
        if any(dev.target_page is None for dev in self.devices):
            raise util.DeviceException(
                "Target page for at least one of the devices could not be"
                "determined, please run 'spread configure' to configure your"
                "devices.")
        with concfut.ThreadPoolExecutor(len(self.devices)) as executor:
            futures = []
            self._logger.debug("Preparing capture in devices")
            for dev in self.devices:
                futures.append(executor.submit(dev.prepare_capture))
        util.check_futures_exceptions(futures)

        flip_target = ('flip_target_pages' in self.config['device'].keys() and
                       self.config['device']['flip_target_pages'].get())
        if flip_target:
            (self.devices[0].target_page,
             self.devices[1].target_page) = (self.devices[1].target_page,
                                             self.devices[0].target_page)
        self._run_hook('prepare_capture', self.devices)
        self._run_hook('start_trigger_loop', self.capture)
        self._update_status(prepared=True)

    @_signal_on_error(on_capture_failed)
    def capture(self, retake=False):
        """ Perform a single capture.

        :param retake:  Replace the previous capture
        """
        if not self.status['prepared']:
            raise util.SpreadsException("Capture was not prepared before.")
        # To prevent multiple captures from interfering with each other,
        # we hold a lock during the whole process.
        with self._capture_lock:
            self._logger.info("Triggering capture.")
            on_capture_triggered.send(self)
            parallel_capture = (
                'parallel_capture' in self.config['device'].keys() and
                self.config['device']['parallel_capture'].get()
            )
            num_devices = len(self.devices)

            # Abort when there is little free space
            if util.get_free_space(self.path) < 50*(1024**2):
                raise IOError("Insufficient disk space to take a capture.")

            futures = []
            captured_pages = []
            with concfut.ThreadPoolExecutor(
                    num_devices if parallel_capture else 1) as executor:
                self._logger.debug("Sending capture command to devices")
                for dev in self.devices:
                    page = self._get_next_capture_page(dev.target_page)
                    captured_pages.append(page)
                    futures.append(executor.submit(dev.capture,
                                                   page.raw_image))
            util.check_futures_exceptions(futures)

            if retake:
                # Remove previous n pages, where n == len(self.devices)
                self.remove_pages(*self.pages[-num_devices:])

            for page in sorted(captured_pages, key=lambda p: p.capture_num):
                page.sequence_num = len(self.pages)
                self.pages.append(page)
            self._run_hook('capture', self.devices, self.path)
            # Queue new images for hashing
            future = self._threadpool.submit(self.bag.add_payload,
                                             *(unicode(p.raw_image)
                                               for p in captured_pages))
            self._pending_tasks.append(future)

        self._save_pages()
        on_capture_succeeded.send(self, pages=captured_pages, retake=retake)

    def finish_capture(self):
        """ Wrap up capture process. """
        # Waits for last capture to finish
        with self._capture_lock:
            concfut.wait(self._pending_tasks)
        with concfut.ThreadPoolExecutor(len(self.devices)) as executor:
            futures = []
            self._logger.debug("Sending finish_capture command to devices")
            for dev in self.devices:
                futures.append(executor.submit(dev.finish_capture))
        util.check_futures_exceptions(futures)
        # NOTE: For performance reason, we only save the pages here, since
        # the ongoing hashing slows things down considerably during capture
        self._save_pages()
        self._run_hook('finish_capture', self.devices, self.path)
        self._run_hook('stop_trigger_loop')
        self._update_status(step=None, prepared=False)

    def process(self):
        """ Run all captured pages through post-processing. """
        self._update_status(step='process', step_progress=0)
        self._logger.info("Starting postprocessing...")
        processed_path = self.path/'data'/'done'
        if not processed_path.exists():
            processed_path.mkdir()
        self._run_hook('process', self.pages, processed_path)
        self.bag.add_payload(unicode(processed_path))
        self._save_pages()
        self._logger.info("Done with postprocessing!")

    def output(self):
        """ Assemble pages into output files. """
        self._logger.info("Generating output files...")
        self._update_status(step='output', step_progress=0)
        out_path = self.path / 'data' / 'out'
        if not out_path.exists():
            out_path.mkdir()
        self._run_hook('output', self.pages, out_path, self.metadata,
                       self.table_of_contents)
        self.bag.add_payload(str(out_path))
        on_modified.send(self, changes={'out_files': self.out_files})
        self._logger.info("Done generating output files!")

    def update_configuration(self, values):
        """ Update the workflow's configuration. """
        # TODO: Validate values against schema in template
        old_cfg = self.config.flatten()
        self.config.set(values)
        diff = util.diff_dicts(old_cfg, self.config.flatten())
        if 'device' in diff:
            self._run_hook('update_configuration', diff['device'])
        on_modified.send(self, changes={'config': self.config.flatten()})

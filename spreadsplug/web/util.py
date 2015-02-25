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

from __future__ import division

import logging
import mimetypes
import os
import time
import traceback
import uuid
from datetime import datetime
from io import BufferedIOBase, UnsupportedOperation

from flask import abort
from flask.json import JSONEncoder
from spreads.vendor.pathlib import Path
from wand.image import Image
from werkzeug.routing import BaseConverter

from spreads.workflow import Workflow, signals as workflow_signals
from spreads.util import EventHandler

try:
    from jpegtran import JPEGImage
    HAS_JPEGTRAN = True
except ImportError:
    HAS_JPEGTRAN = False
logger = logging.getLogger('spreadsplug.web.util')

# NOTE: This is a workaround for a known datetime/time race condition, see
#       this CPython bugreport for more details:
#       http://bugs.python.org/issue7980
datetime.strptime("2014", "%Y")


class Event(object):
    """ Wrapper class for emitted events.

    :param :class:`blinker.NamedSignal` signal: The emitted signal
    :param sender:      The object that emitted the signal or None
    :param dict data:   Parameters the signal was emitted with
    """
    __slots__ = ['signal', 'sender', 'data', 'id']

    def __init__(self, signal, sender, data, id=None):
        self.signal = signal
        self.sender = sender
        self.data = data
        self.id = id


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif isinstance(obj, Workflow):
            return self._workflow_to_dict(obj)
        elif isinstance(obj, logging.LogRecord):
            return self._logrecord_to_dict(obj)
        elif isinstance(obj, Event):
            return self._event_to_dict(obj)
        elif isinstance(obj, Path):
            return mimetypes.guess_type(unicode(obj))[0]
        elif isinstance(obj, datetime):
            # Return datetime as an epoch timestamp with microsecond-resolution
            return (time.mktime(obj.timetuple())*1000 + obj.microsecond)/1000.0
        else:
            return JSONEncoder.default(self, obj)

    def _workflow_to_dict(self, workflow):
        return {
            'id': workflow.id,
            'slug': workflow.slug,
            'metadata': dict(workflow.metadata),
            'status': workflow.status,
            'last_modified': workflow.last_modified,
            'pages': workflow.pages,
            'out_files': [{'name': path.name,
                           'mimetype': path}
                          for path in workflow.out_files],
            'config': {k: v for k, v in workflow.config.flatten().iteritems()
                       if k in workflow.config['plugins'].get() or
                       k in ('device', 'plugins')}
        }

    def _logrecord_to_dict(self, record):
        return {
            'time': datetime.fromtimestamp(record.created),
            'message': record.getMessage(),
            'origin': record.name,
            'level': record.levelname,
            'traceback': ("".join(traceback.format_exception(*record.exc_info))
                          if record.exc_info else None)
        }

    def _event_to_dict(self, event):
        name = event.signal.name
        data = event.data
        if event.signal in workflow_signals.values():
            if 'senderId' not in data:
                data['senderId'] = event.sender.id
        elif event.signal is EventHandler.on_log_emit:
            data = data['record']
        return {'name': name, 'data': data, 'id': event.id}


class WorkflowConverter(BaseConverter):
    def to_python(self, value):
        from spreadsplug.web.app import app
        try:
            uuid.UUID(value)
            workflow = Workflow.find_by_id(app.config['base_path'], value)
        except ValueError:
            workflow = Workflow.find_by_slug(app.config['base_path'], value)
        if workflow is None:
            abort(404)
        return workflow

    def to_url(self, value):
        return value.slug


class GeneratorIO(BufferedIOBase):
    """ Wrapper around a generator to act as a file-like object.
    """
    def __init__(self, generator, length=None):
        self._generator = generator
        self._next_chunk = bytearray()
        self._length = length

    def read(self, num_bytes=None):
        if self._next_chunk is None:
            return b''
        try:
            if num_bytes is None:
                rv = self._next_chunk[:]
                self._next_chunk[:] = next(self._generator)
                return bytes(rv)
            while len(self._next_chunk) < num_bytes:
                self._next_chunk += next(self._generator)
            rv = self._next_chunk[:num_bytes]
            self._next_chunk[:] = self._next_chunk[num_bytes:]
            return bytes(rv)
        except StopIteration:
            rv = self._next_chunk[:]
            self._next_chunk = None
            return bytes(rv)

    def __len__(self):
        if self._length is not None:
            return self._length
        else:
            raise UnsupportedOperation


def convert_image(img_path, img_format):
    with Image(filename=unicode(img_path)) as img:
        return img.make_blob(format=img_format)


def scale_image(img_path, width=None, height=None):
    def get_target_size(srcwidth, srcheight):
        aspect = srcwidth/srcheight
        target_width = width if width else int(aspect*height)
        target_height = height if height else int(width/aspect)
        return target_width, target_height

    if width is None and height is None:
        raise ValueError("Please specify either width or height")
    if HAS_JPEGTRAN and img_path.suffix.lower() in ('.jpg', '.jpeg'):
        img = JPEGImage(unicode(img_path))
        width, height = get_target_size(img.width, img.height)
        return img.downscale(width, height).as_blob()
    else:
        with Image(filename=unicode(img_path)) as img:
            width, height = get_target_size(img.width, img.height)
            img.sample(width, height)
            return img.make_blob(format='jpg')


def get_thumbnail(img_path):
    """ Return thumbnail for image.

    :param img_path:  Path to image
    :type img_path:   pathlib.Path
    :return:          The thumbnail
    :rtype:           bytestring
    """
    if HAS_JPEGTRAN and img_path.suffix.lower() in ('.jpg', '.jpeg'):
        img = JPEGImage(unicode(img_path))
        thumb = img.exif_thumbnail
        if thumb:
            logger.debug("Using EXIF thumbnail for {0}".format(img_path))
            return thumb.as_blob()

    logger.debug("Generating thumbnail for {0}".format(img_path))
    return scale_image(img_path, width=160)


def find_stick():
    import dbus
    bus = dbus.SystemBus()
    iudisks = dbus.Interface(
        bus.get_object("org.freedesktop.UDisks",
                       "/org/freedesktop/UDisks"),
        "org.freedesktop.UDisks")
    devices = [bus.get_object("org.freedesktop.UDisks", dev)
               for dev in iudisks.EnumerateDevices()]
    idevices = [dbus.Interface(dev, "org.freedesktop.DBus.Properties")
                for dev in devices]
    try:
        istick = next(i for i in idevices if i.Get("", "DeviceIsPartition") and
                      i.Get("", "DriveConnectionInterface") == "usb")
    except StopIteration:
        return
    return dbus.Interface(
        bus.get_object("org.freedesktop.UDisks",
                       iudisks.FindDeviceByDeviceFile(
                           istick.Get("", "DeviceFile"))),
        "org.freedesktop.DBus.UDisks.Device")


def find_stick_win():
    import win32api
    import win32file
    for drive in win32api.GetLogicalDriveStrings().split("\x00")[:-1]:
        if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE:
            return drive


def calculate_zipsize(frecords):
    """ Calculate size of resulting ZIP.

    We can only safely pre-calculate this because we use no compression,
    assume that we neither store empty directories and files bigger
    than 4GiB.
    Many thanks to 'flocki' from StackOverflow, who provided the underlying
    formula: https://stackoverflow.com/a/19380600/487903
    """
    size = 0
    for args, kwargs in frecords:
        filename = args[0]
        arcname = kwargs['arcname']
        isdir = os.path.isdir(filename)
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]
        if isdir:
            arcname += '/'
        size += (2*len(arcname))  # Once in file header, once in EOCD
        size += 30  # Fixed part of local file header
        size += 16  # Data descriptor
        size += 46  # Central file directory header
        size += os.path.getsize(filename)
    size += 22  # End of central directory record (EOCD)
    return size

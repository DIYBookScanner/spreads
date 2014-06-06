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

import calendar
import logging
import time
import traceback
import uuid
from datetime import datetime
from io import BufferedIOBase, UnsupportedOperation

from spreads.vendor.pathlib import Path
from flask import abort
from flask.json import JSONEncoder
from jpegtran import JPEGImage
from werkzeug.routing import BaseConverter

from spreads.workflow import Workflow, signals as workflow_signals
from spreads.util import EventHandler

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
    __slots__ = ['signal', 'sender', 'data', 'emitted']

    def __init__(self, signal, sender, data, emitted=None):
        self.signal = signal
        self.sender = sender
        self.data = data
        if emitted is None:
            emitted = time.time()
        self.emitted = emitted


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Workflow):
            return self._workflow_to_dict(obj)
        elif isinstance(obj, logging.LogRecord):
            return self._logrecord_to_dict(obj)
        elif isinstance(obj, Event):
            return self._event_to_dict(obj)
        elif isinstance(obj, datetime):
            # Return datetime as an epoch timestamp with microsecond-resolution
            ts = (calendar.timegm(obj.timetuple())*1000
                  + obj.microsecond)/1000.0
            return ts
        else:
            return JSONEncoder.default(self, obj)

    def _workflow_to_dict(self, workflow):
        return {
            'id': workflow.id,
            'slug': workflow.slug,
            'name': workflow.path.name,
            'status': workflow.status,
            'raw_images': [get_image_url(workflow, x)
                           for x in workflow.raw_images],
            'processed_images': [get_image_url(workflow, x)
                                 for x in workflow.processed_images],
            'out_files': ([unicode(path) for path in workflow.out_files]
                          if workflow.out_files else []),
            'config': {k: v for k, v in workflow.config.flatten().iteritems()
                       if k in workflow.config['plugins'].get()
                       or k in ('device', 'plugins')}
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
            if 'id' not in data:
                data['id'] = event.sender.id
            if 'images' in data:
                data['images'] = [get_image_url(event.sender, imgpath)
                                  for imgpath in data['images']]
        elif event.signal is EventHandler.on_log_emit:
            data = data['record']
        return {'name': name, 'data': data}


class WorkflowConverter(BaseConverter):
    def to_python(self, value):
        from spreadsplug.web import app
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


def get_image_url(workflow, img_path):
    img_num = int(Path(img_path).stem)
    return "/api/workflow/{0}/image/{1}".format(workflow.slug, img_num)


def scale_image(img_name, width=None, height=None):
    if width is None and height is None:
        raise ValueError("Please specify either width or height")
    img = JPEGImage(img_name)
    aspect = img.width/img.height
    width = width if width else int(aspect*height)
    height = height if height else int(width/aspect)
    return img.downscale(width, height).as_blob()


def get_thumbnail(img_path):
    """ Return thumbnail for image.

    :param img_path:  Path to image
    :type img_path:   pathlib.Path
    :return:          The thumbnail
    :rtype:           bytestring
    """
    img = JPEGImage(unicode(img_path))
    thumb = img.exif_thumbnail
    if thumb:
        logger.debug("Using EXIF thumbnail for {0}".format(img_path))
        return thumb.as_blob()
    else:
        logger.debug("Generating thumbnail for {0}".format(img_path))
        return scale_image(unicode(img_path), width=160)


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
        istick = next(i for i in idevices if i.Get("", "DeviceIsPartition")
                      and i.Get("", "DriveConnectionInterface") == "usb")
    except StopIteration:
        return
    return dbus.Interface(
        bus.get_object("org.freedesktop.UDisks",
                       iudisks.FindDeviceByDeviceFile(
                           istick.Get("", "DeviceFile"))),
        "org.freedesktop.DBus.UDisks.Device")

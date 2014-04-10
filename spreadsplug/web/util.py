from __future__ import division

import calendar
import logging
import time
import traceback
from datetime import datetime

from flask import abort
from flask.json import JSONEncoder
from werkzeug.routing import BaseConverter, ValidationError

from spreads.workflow import Workflow
from spreads.util import EventHandler

from persistence import get_workflow

HAS_JPEGTRAN = False
try:
    from jpegtran import JPEGImage
    HAS_JPEGTRAN = True
except ImportError:
    import StringIO
    import pyexiv2
    import PIL

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
            'name': workflow.path.name,
            'step': workflow.step,
            'step_done': workflow.step_done,
            'images': [get_image_url(workflow, x)
                       for x in workflow.images] if workflow.images else [],
            'out_files': ([unicode(path) for path in workflow.out_files]
                          if workflow.out_files else []),
            'config': workflow.config.flatten()
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
        if event.signal in Workflow.signals.values():
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
        workflow_id = None
        try:
            workflow_id = int(value)
        except ValueError:
            raise ValidationError()
        workflow = get_workflow(workflow_id)
        if workflow is None:
            abort(404)
        return workflow

    def to_url(self, value):
        return unicode(value.id)


def get_image_url(workflow, img_path):
    img_num = int(img_path.stem)
    return "/api/workflow/{0}/image/{1}".format(workflow.id, img_num)


def scale_image(img_name, width=None, height=None):
    if width is None and height is None:
        raise ValueError("Please specify either width or height")
    img, aspect = None, None
    if HAS_JPEGTRAN:
        img = JPEGImage(img_name)
        aspect = img.width/img.height
    else:
        img = PIL.Image.open(img_name)
    width = width if width else int(aspect*height)
    height = height if height else int(width/aspect)
    if HAS_JPEGTRAN:
        return img.downscale(width, height).as_blob()
    else:
        buf = StringIO.StringIO()
        img.resize((width, height), PIL.Image.ANTIALIAS)
        img.save(buf, format='JPEG')
        return buf.getvalue()


def get_thumbnail(img_path):
    """ Return thumbnail for image.

    :param img_path:  Path to image
    :type img_path:   pathlib.Path
    :return:          The thumbnail
    :rtype:           bytestring
    """

    thumb = None
    if not HAS_JPEGTRAN:
        logger.debug("Extracting EXIF thumbnail for {0}".format(img_path))
        metadata = pyexiv2.ImageMetadata(unicode(img_path))
        metadata.read()
        thumb = metadata.previews[0].data
    else:
        thumb = JPEGImage(unicode(img_path)).exif_thumbnail.as_blob()
    if thumb:
        logger.debug("Using EXIF thumbnail for {0}".format(img_path))
        return thumb
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


def find_stick_win():
    import win32api
    import win32file
    for drive in win32api.GetLogicalDriveStrings().split("\x00")[:-1]:
        if win32file.GetDriveType(drive) == win32file.DRIVE_REMOVABLE:
            return drive

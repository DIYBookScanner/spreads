from __future__ import division

import logging
import platform
import re
import subprocess
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import wraps

from flask import request, url_for, abort
from flask.json import JSONEncoder
from jpegtran import JPEGImage
from werkzeug.contrib.cache import SimpleCache
from werkzeug.routing import BaseConverter, ValidationError

from spreads.workflow import Workflow
from spreads.util import EventHandler

from persistence import get_workflow

PYPY = platform.python_implementation() == "PyPy"

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


# NOTE: The cache object is global
cache = SimpleCache()


def cached(timeout=5 * 60, key='view/%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator


def get_image_url(workflow, img_path):
    img_num = int(img_path.stem)
    return url_for('.get_workflow_image', workflow=workflow, img_num=img_num)


def get_log_lines(logbuffer=None, since=0, levels=['WARNING', 'ERROR']):
    if not logbuffer:
        logbuffer = next(
            x for x in logging.getLogger().handlers
            if isinstance(x, logging.handlers.BufferingHandler)).buffer
    messages = [logrecord_to_dict(msg)
                for msg in sorted(logbuffer, key=lambda x: x.relativeCreated,
                                  reverse=True)
                if msg.levelname in levels and msg.relativeCreated > since]
    return messages


def get_thumbnail(img_path):
    """ Return thumbnail for image.

    :param img_path:  Path to image
    :type img_path:   pathlib.Path
    :return:          The thumbnail
    :rtype:           bytestring
    """
    thumb = JPEGImage(unicode(img_path)).exif_thumbnail.as_blob()
    if thumb:
        logger.debug("Using EXIF thumbnail for {0}".format(img_path))
        return thumb
    else:
        logger.debug("Generating thumbnail for {0}".format(img_path))
        return scale_image(unicode(img_path), width=160)


if PYPY:
    def find_stick():
        """ Since the 'dbus' module is implemented via CPython's extension API,
        we cannot use it when running in PyPy. The same goes for GOBject
        introspection via PyGobject. 'pgi' is not yet mature enough to deal
        with some of UDisks' interfaces.  Thats why we go a very hacky way: Use
        the 'gdbus' CLI utility, parse its output and return the device path.

        """
        out = subprocess.check_output(
            "gdbus introspect --system --dest org.freedesktop.UDisks "
            "--object-path /org/freedesktop/UDisks/devices --recurse "
            "--only-properties".split())
        devs = zip(*((re.match(r".* = '?(.*?)'?;", x).group(1)
                     for x in out.splitlines()
                     if "DriveConnectionInterface =" in x
                     or "DeviceIsPartition =" in x
                     or "DeviceFile = " in x),)*3)
        try:
            return next(dev[2] for dev in devs if dev[0] == 'usb'
                        and dev[1] == 'true')
        except StopIteration:
            return None

    @contextmanager
    def _mount_stick_shell(stick):
        """ Context Manager that mounts the first available partition on a USB
        drive, yields its path and then unmounts it.

        """
        out = subprocess.check_output("udisks --mount {0}"
                                      .format(stick).split())
        path = re.match(r"Mounted .* at (.*)", out).group(1)
        try:
            yield path
        except Exception as e:
            raise e
        finally:
            subprocess.check_output("udisks --unmount {0}"
                                    .format(stick).split())

else:
    import dbus

    def find_stick():
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

    @contextmanager
    def mount_stick(stick):
        """ Context Manager that mounts the first available partition on a USB
        drive, yields its path and then unmounts it.

        """
        mount = stick.get_dbus_method(
            "FilesystemMount", dbus_interface="org.freedesktop.UDisks.Device")
        path = mount('', [])
        try:
            yield path
        except Exception as e:
            raise e
        finally:
            unmount = stick.get_dbus_method(
                "FilesystemUnmount",
                dbus_interface="org.freedesktop.UDisks.Device")
            unmount([], timeout=1e6)  # dbus-python doesn't know an infinite
                                    # timeout... unmounting sometimes takes a
                                    # long time, since the device has to be
                                    # synced.

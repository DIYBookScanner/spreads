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

import itertools
import json
import logging
import os
import uuid
import tarfile
import tempfile
import threading
import time
import zipfile
import Queue

import blinker
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, asynchronous, stream_request_body
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler

import util
from spreads.workflow import Workflow

signals = blinker.Namespace()
on_download_finished = signals.signal('download:finished')

event_buffer = None  # NOTE: Will be set after we defined EventHandler


class BoundaryStripper(object):
    def __init__(self):
        self.initialized = False

    def process(self, data):
        trimmed = data.splitlines()
        tmp = data.splitlines(True)
        if not self.initialized:
            self.boundary = trimmed[0].strip()
            tmp = tmp[1:]
            trimmed = trimmed[1:]
            self.initialized = True
            try:
                firstelem = trimmed[:5].index("")
                tmp = tmp[firstelem + 1:]
                trimmed = trimmed[firstelem + 1:]
            except ValueError:
                pass
        try:
            lastelem = trimmed.index(self.boundary + "--")
            self.initialized = False
            return "".join(tmp[:lastelem])
        except ValueError:
            return "".join(tmp)


class WebSocketHandler(TornadoWebSocketHandler):
    # This is a class attribute valid for all SocketHandler objects, used
    # to store a reference to all open websockets.
    clients = []
    lock = threading.Lock()

    def open(self):
        if self not in self.clients:
            self.clients.append(self)

    def on_close(self):
        if self in self.clients:
            self.clients.remove(self)

    @staticmethod
    def send_event(event):
        data = json.dumps(event, cls=util.CustomJSONEncoder)
        for client in WebSocketHandler.clients:
            with WebSocketHandler.lock:
                client.write_message(data)


class EventBuffer(object):
    def __init__(self):
        self.waiters = set()
        self.cache = []
        self.cache_size = 200
        self.counter = itertools.count()
        self.count_lock = threading.Lock()

    def wait_for_events(self, callback, cursor=None):
        if cursor:
            cursor = int(cursor)
            new_count = 0
            for event in reversed(self.cache):
                if event.id == cursor:
                    break
                new_count += 1
            if new_count:
                callback(self.cache[-new_count:])
                return
        self.waiters.add(callback)

    def cancel_wait(self, callback):
        self.waiters.remove(callback)

    def new_events(self, events):
        for event in events:
            with self.count_lock:
                event.id = next(self.counter)
        for callback in self.waiters:
            try:
                callback(events)
            except:
                logging.error("Error in waiter callback", exc_info=True)
        self.waiters = set()
        self.cache.extend(events)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size:]
# Global event buffer (previously defined at the top of the module)
event_buffer = EventBuffer()


class EventLongPollingHandler(RequestHandler):
    @asynchronous
    def post(self):
        cursor = self.get_argument("cursor", None)
        event_buffer.wait_for_events(self.on_new_events, cursor=cursor)

    def on_new_events(self, events):
        if self.request.connection.stream.closed():
            return
        self.finish(json.dumps(dict(events=events),
                               cls=util.CustomJSONEncoder))

    def on_connection_close(self):
        event_buffer.cancel_wait(self.on_new_events)


@stream_request_body
class StreamingUploadHandler(RequestHandler):
    def initialize(self, base_path):
        self.base_path = base_path

    def prepare(self):
        self.stripper = BoundaryStripper()
        self.request.connection.set_max_body_size(2*1024**3)
        fdesc, self.fname = tempfile.mkstemp()
        self.fp = os.fdopen(fdesc, 'wb')

    def data_received(self, chunk):
        self.fp.write(self.stripper.process(chunk))
        self.fp.flush()

    def post(self):
        self.fp.close()
        with zipfile.ZipFile(self.fname) as zf:
            wfname = os.path.dirname(zf.namelist()[0])
            zf.extractall(path=self.base_path)
        os.unlink(self.fname)

        workflow = Workflow(path=os.path.join(self.base_path, wfname))
        from spreads.workflow import on_created
        on_created.send(workflow, workflow=workflow)

        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(workflow, cls=util.CustomJSONEncoder))


class ZipDownloadHandler(RequestHandler):
    def initialize(self, base_path):
        self.base_path = base_path

    @staticmethod
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

    @asynchronous
    def get(self, workflow_id, filename):
        uuid.UUID(workflow_id)
        workflow = Workflow.find_by_id(self.base_path, workflow_id)
        zstream = workflow.bag.package_as_zipstream(compression=None)

        self.set_status(200)
        self.set_header('Content-type', 'application/zip')
        self.set_header('Content-length',
                        str(self.calculate_zipsize(zstream.paths_to_write)))

        self.zstream_iter = iter(zstream)

        self.send_next_chunk()

    def send_next_chunk(self):
        try:
            self.write(next(self.zstream_iter))
            self.flush(callback=self.send_next_chunk)
        except StopIteration:
            self.finish()
        on_download_finished.send()


class QueueIO(object):
    """ File-like object that writes to a queue.

    Data can be read from another thread by iterating over the object.
    Intended to be passed into tarfile.open as to allow streaming tar files
    over the network without buffering them in RAM or on disk.
    """
    def __init__(self, handler):
        #That's right, length 1, we want to save memory, after all...
        self.queue = Queue.Queue(maxsize=1)
        self.closed = False
        self.last_read = None
        self.read_time = None

    def write(self, data):
        while not self.closed:
            # To achieve a balance between wasted CPU cycles (checking the
            # queue) and decreased transfer speed (sleeping for too long),
            # we wait at most the minimum time (plus a little extra) between
            # two reads (see also: comment in `next`)
            try:
                self.queue.put(data, block=False)
                return
            except Queue.Full:
                if self.read_time is not None:
                    time.sleep(self.read_time*1.1)
        raise ValueError("I/O operation on closed file")

    def close(self):
        self.closed = True

    def __iter__(self):
        return self

    def next(self):
        if self.closed and self.queue.empty():
            raise StopIteration
        if self.last_read is None:
            self.last_read = time.time()
        else:
            # See if we have gotten any faster since the last read
            read_time = time.time() - self.last_read
            if self.read_time is None or self.read_time > read_time:
                self.read_time = read_time
            self.last_read += read_time
        return self.queue.get()


class TarDownloadHandler(RequestHandler):
    def initialize(self, base_path):
        self.base_path = base_path

    def create_tar(self, workflow, cb, exception_cb):
        """ Intended to be run in a separate thread, since the call will block
        until the whole workflow has been written out to the client or
        the user cancels the transfer.
        """
        try:
            workflow.bag.package_as_tarstream(self.fp)
            IOLoop.instance().add_callback(cb)
        except ValueError as e:
            IOLoop.instance().add_callback(exception_cb, (e,))

    def calculate_tarsize(self, workflow):
        """ Similar to ZipDownloadHandler.calculate_zipsize, we can safely
        pre-calculate the size of the resulting tar-file since we don't
        compress and the resulting file is in the POSIX.1-1988 ustar format.
        """
        # top-level directory block
        size = tarfile.BLOCKSIZE
        for path in workflow.path.glob('**/*'):
            # file header
            size += tarfile.BLOCKSIZE
            # file size rounded up to next multiple of 512
            if not path.is_dir():
                size += ((path.stat().st_size/512)+1)*512
        # empty end-of-file blocks
        size += 2*tarfile.BLOCKSIZE
        # fill up until the size is a multiple of tarfile.RECORDSIZE
        blocks, remainder = divmod(size, tarfile.RECORDSIZE)
        if remainder > 0:
            size += (tarfile.RECORDSIZE - remainder)
        return size

    @asynchronous
    def get(self, workflow_id, filename):
        uuid.UUID(workflow_id)
        workflow = Workflow.find_by_id(self.base_path, workflow_id)

        self.set_status(200)
        self.set_header('Content-type', 'application/tar')
        self.set_header('Content-length', self.calculate_tarsize(workflow))

        self.fp = QueueIO(self)
        self.thread = threading.Thread(
            target=self.create_tar,
            args=(workflow, self.on_done, self.on_exception)
        )
        self.thread.start()
        self.send_next_chunk()

    def send_next_chunk(self):
        try:
            self.write(next(self.fp))
            self.flush(callback=self.send_next_chunk)
        except StopIteration:
            self.finish()

    def on_done(self):
        self.fp.close()

    def on_exception(self, exc):
        skip = (isinstance(exc[0], ValueError)
                and "closed file" in exc[0].message)
        if not skip:
            raise exc

    def on_finish(self):
        on_download_finished.send()

    def on_connection_close(self):
        self.fp.close()

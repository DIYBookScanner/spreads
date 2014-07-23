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
from threading import Lock

import blinker
from tornado.web import RequestHandler, asynchronous
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler

import util
from spreads.workflow import Workflow

signals = blinker.Namespace()
on_download_finished = signals.signal('download:finished')

event_buffer = None  # NOTE: Will be set after we defined EventHandler


class WebSocketHandler(TornadoWebSocketHandler):
    # This is a class attribute valid for all SocketHandler objects, used
    # to store a reference to all open websockets.
    clients = []
    lock = Lock()

    def open(self):
        if self not in self.clients:
            self.clients.append(self)

    def on_close(self):
        if self in self.clients:
            self.clients.remove(self)


class EventBuffer(object):
    def __init__(self):
        self.waiters = set()
        self.cache = []
        self.cache_size = 200
        self.counter = itertools.count()
        self.count_lock = Lock()

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
        # Closed client connection
        if self.request.connection.stream.closed():
            return
        self.finish(json.dumps(dict(events=events),
                               cls=util.CustomJSONEncoder))

    def on_connection_close(self):
        event_buffer.cancel_wait(self.on_new_events)


class DownloadHandler(RequestHandler):
    def initialize(self, base_path):
        self.base_path = base_path

    @staticmethod
    def calculate_zipsize(frecords):
        """ Calculate size of resulting ZIP.

        We can only safely pre-calculate this because we use no compression,
        assume that we neither store empty directories and nor files bigger
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

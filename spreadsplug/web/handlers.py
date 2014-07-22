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

import os
import uuid
from threading import Lock

import blinker
from tornado.web import RequestHandler, asynchronous
from tornado.websocket import WebSocketHandler as TornadoWebSocketHandler

from spreads.workflow import Workflow

signals = blinker.Namespace()
on_download_finished = signals.signal('download:finished')


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

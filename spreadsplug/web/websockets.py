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

import json
import threading

from tornado import websocket, web, ioloop

from util import CustomJSONEncoder


class SocketHandler(websocket.WebSocketHandler):
    # This is a class attribute valid for all SocketHandler objects, used
    # to store a reference to all open websockets.
    clients = []

    def open(self):
        if self not in self.clients:
            self.clients.append(self)

    def on_close(self):
        if self in self.clients:
            self.clients.remove(self)


class WebSocketServer(threading.Thread):
    def __init__(self, port):
        super(WebSocketServer, self).__init__()
        app = web.Application([
            (r'/', SocketHandler),
        ])
        app.listen(port)
        self._loop = ioloop.IOLoop.instance()
        self._lock = threading.Lock()

    def stop(self):
        self._loop.stop()
        self.join()

    def run(self):
        self._loop.start()

    def send_event(self, event):
        data = json.dumps(event, cls=CustomJSONEncoder)
        for sock in SocketHandler.clients:
            # NOTE: The lock is neccessary since Tornado is not thread-safe.
            #       This should be obvious to anyone only vaguely familiar with
            #       it, but it cost me quite a bit of debugging time to find
            #       out :-)
            with self._lock:
                sock.write_message(data)

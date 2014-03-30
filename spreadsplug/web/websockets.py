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
    def __init__(self, port=5001):
        super(WebSocketServer, self).__init__()
        app = web.Application([
            (r'/', SocketHandler),
        ])
        app.listen(port)
        self._loop = ioloop.IOLoop.instance()

    def stop(self):
        self._loop.stop()
        self.join()

    def run(self):
        self._loop.start()

    def send_event(self, event):
        data = json.dumps(event, cls=CustomJSONEncoder)
        for sock in SocketHandler.clients:
            sock.write_message(data)

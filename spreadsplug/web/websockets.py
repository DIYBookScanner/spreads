import threading

from flask import json
from tornado import websocket, web, ioloop

from spreads.util import EventHandler
from spreads.workflow import Workflow

import util


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

        # NOTE: We have to connect our receivers during initialization and not
        #       by decorating the methods themselves, since they would then
        #       be called in their unbound state.
        EventHandler.on_log_emit.connect(self.emit_logrecord)
        Workflow.on_step_progressed.connect(self.emit_progress)
        Workflow.on_created.connect(self.emit_workflow_created)
        Workflow.on_modified.connect(self.emit_workflow_modified)
        Workflow.on_removed.connect(self.emit_workflow_removed)
        Workflow.on_capture_executed.connect(self.emit_workflow_capture)

    def stop(self):
        self._loop.stop()

    def run(self):
        self._loop.start()

    def send_message(self, event_name, event_data):
        message = {
            'event': event_name,
            'data': event_data
        }
        for sock in SocketHandler.clients:
            sock.write_message(json.dumps(message))

    def emit_logrecord(self, _, **kwargs):
        self.send_message('logrecord-emitted',
                          util.logrecord_to_dict(kwargs['record']))

    def emit_progress(self, workflow, **kwargs):
        progress_info = {
            'workflow_id': workflow.id,
            'step': workflow.step,
            'plugin': kwargs['plugin_name'],
            'progress': kwargs['progress']
        }
        self.send_message("workflow.step-progressed", progress_info)

    def emit_workflow_created(self, _, **kwargs):
        self.send_message("workflow.created",
                          util.workflow_to_dict(kwargs['workflow']))

    def emit_workflow_modified(self, workflow, **kwargs):
        self.send_message("workflow.config-modified",
                          {'id': workflow.id,
                           'changes': kwargs['changes']})

    def emit_workflow_removed(self, _, **kwargs):
        self.send_message("workflow.removed", {'id': kwargs['workflow_id']})

    def emit_workflow_capture(self, workflow, **kwargs):
        self.send_message("workflow.capture",
                          {'id': workflow.id,
                           'images': [util.get_image_url(x)
                                      for x in kwargs['images']]})

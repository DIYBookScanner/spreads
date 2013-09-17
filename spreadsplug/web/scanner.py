import os
import time
from contextlib import contextmanager

from flask import Blueprint, g, abort, jsonify

import spreads
from spreads import plugin, workflow

scan_api = Blueprint('scan_api', __name__)

g.devices = plugin.get_devices()
g.devices_locked = False
g.devices_prepared = False
g.current_step = None
g.time_first_capture = None
g.number_captures = 0


@contextmanager
def lock_devices():
    g.devices_locked = True
    yield
    g.devices_locked = False


@scan_api.route('/messages')
def get_log():
    # TODO: Use message flashing functions for this
    # TODO: Return last 100 >=INFO logging messages
    raise NotImplementedError


@scan_api.route('/')
def get_status():
    status = { 'current_step': g.current_step,
               'devices_locked': g.devices_locked,
               'devices_prepared': g.devices_prepared,
               'time_first_capture': g.time_first_capture,
               'number_captures': g.number_captures,
             }
    return jsonify(status=status)


@scan_api.route('/prepare', methods=['POST'])
def prepare_capture():
    if g.devices_prepared:
        raise NotImplementedError
    if g.devices_locked:
        abort(423)
    # TODO: Get configuration from request
    g.current_step = 'prepare'
    with lock_devices():
        workflow.prepare_capture(devices=g.devices)


@scan_api.route('/capture', methods=['GET'])
def capture():
    if not g.devices_prepared:
        raise NotImplementedError
    if g.devices_locked:
        abort(423)
    if not g.current_step == 'capture':
        g.current_step = 'capture'
        g.time_first_capture = time.time()
    with lock_devices():
        workflow.capture(devices=g.devices)


@scan_api.route('/download/<name>', methods=['POST'])
def start_download(name):
    if g.devices_locked:
        abort(423)
    # TODO: Get parameters from request (keep, inverse order)
    # TODO: Find a way to make this asynchronous in a proper way
    with lock_devices():
        workflow.download(devices=g.devices,
                          path=spreads.config['project_path'])


@scan_api.route('/download/<name>', methods=['GET'])
def download_status(name):
    # TODO: Return download status
    # TODO: Return progress?
    raise NotImplementedError


@scan_api.route('/images/<name>', methods=['GET'])
def get_image_list(name):
    image_list = os.listdir(os.path.join(spreads.config['project_path'], name))
    return jsonify(images=image_list)


@scan_api.route('/images/<name>', methods=['POST', 'PATCH'])
def update_image_list(name):
    # TODO: Get updated order from request
    # TODO: Apply changes to images
    raise NotImplementedError


@scan_api.route('/images/<name>/<img_name>', methods=['GET'])
def get_image(name, img_name):
    # TODO: Load image, return as image
    raise NotImplementedError

@scan_api.route('/images/<name>/<img_name>', methods=['DELETE'])
def delete_image(name, img_name):
    # TODO: Delete the image
    raise NotImplementedError

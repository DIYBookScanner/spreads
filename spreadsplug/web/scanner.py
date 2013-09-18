import os
import time
from contextlib import contextmanager

from flask import Blueprint, g, abort, jsonify, make_response, request
from werkzeug.http import HTTP_STATUS_CODES
HTTP_STATUS_CODES = {value: key
                     for key, value in HTTP_STATUS_CODES.iteritems()}

import spreads
from spreads import plugin, workflow

scan_api = Blueprint('scan_api', __name__)

devices = plugin.get_devices()
devices_locked = False
devices_prepared = False
current_step = None
time_first_capture = None
number_captures = 0


@contextmanager
def lock_devices():
    devices_locked = True
    yield
    devices_locked = False


def _set_configuration(config):
    raise NotImplementedError

def _get_configuration():
    raise NotImplementedError


@scan_api.route('/messages')
def get_log():
    # TODO: Use message flashing functions for this?
    # TODO: Return last 100 >=INFO logging messages
    raise NotImplementedError


@scan_api.route('/')
def get_status():
    status = {'current_step': current_step,
              'devices_locked': devices_locked,
              'devices_prepared': devices_prepared,
              'time_first_capture': time_first_capture,
              'number_captures': number_captures,
              }
    return jsonify(status=status)


@scan_api.route('/configuration', methods=['GET', 'POST'])
def configuration():
    if request.method == 'POST':
        _set_configuration(request.get_json())
    else:
        return jsonify(configuration=_get_configuration())


@scan_api.route('/configuration/template', methods=['GET'])
def get_configuration_template():
    out_dict = {
        'general': {
            'dpi': plugin.PluginOption(300, "Device resolution", False)},
    }
    # NOTE: This one is wicked... The goal is to find all extensions that
    #       implement one of the steps relevant to this component.
    #       To do so, we compare the code objects for the appropriate
    #       hook method with the same method in the HookPlugin base class.
    #       If the two are not the same, we can (somewhat) safely assume
    #       that the extension implements this hook and is thus relevant
    #       to us.
    #       Yes, this is not ideal and is due to our somewhat sloppy
    #       plugin interface. That's why...
    # TODO: Refactor plugin interface to make this less painful
    relevant_extensions = (
        ext
        for ext in plugin.get_pluginmanager()
        for step in ('prepare_capture', 'capture', 'finish_capture',
                     'download', 'delete')
        if not (getattr(ext.plugin, step).func_code is
                getattr(plugin.HookPlugin, step).func_code)
    )
    for ext in relevant_extensions:
        tmpl = ext.plugin.configuration_template()
        if not tmpl:
            continue
        out_dict[ext.name] = tmpl
    return jsonify(template=out_dict)


@scan_api.route('/prepare', methods=['POST'])
def prepare_capture():
    if devices_prepared:
        return
    if devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    # TODO: Get configuration from request
    current_step = 'prepare'
    with lock_devices():
        workflow.prepare_capture(devices=devices)


@scan_api.route('/capture', methods=['GET'])
def capture():
    if not devices_prepared:
        return make_response("The devices are not yet prepared.",
                             HTTP_STATUS_CODES['Precondition Required'])
    if devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    if not current_step == 'capture':
        current_step = 'capture'
        time_first_capture = time.time()
    with lock_devices():
        workflow.capture(devices=devices)


@scan_api.route('/download/<name>', methods=['POST'])
def start_download(name):
    if devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    # TODO: Get parameters from request (keep, inverse order)
    # TODO: Find a way to make this asynchronous in a proper way
    with lock_devices():
        workflow.download(devices=devices,
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

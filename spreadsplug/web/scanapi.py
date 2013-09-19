import logging
import os
import time
from contextlib import contextmanager
from threading import Thread

from flask import Blueprint, abort, jsonify, make_response, request
from werkzeug.http import HTTP_STATUS_CODES
HTTP_STATUS_CODES = {value: key
                     for key, value in HTTP_STATUS_CODES.iteritems()}

import spreads
from spreads import plugin, workflow

import common


class CaptureProject(object):
    """ Small helper singleton class that stores global state. """
    def __init__(self, name):
        self.name = name
        self.path = os.path.join(spreads.config['web']['path'], name)
        # FIXME: Those two attributes should go into the SpreadsDevice class
        self.devices_locked = False
        self.devices_prepared = False
        self.current_step = None
        self.time_first_capture = None
        self.number_captures = 0
        self.download_thread = None


logger = logging.getLogger('spreadsplug.web.scanapi')

scan_api = Blueprint('scan_api', __name__)

devices = plugin.get_devices()
project = None


@contextmanager
def lock_devices():
    project.devices_locked = True
    yield
    project.devices_locked = False


def _set_configuration(config):
    for key, value in config.iteritems():
        if key == 'project_name':
            # TODO: Raise exception of project_name has not been set
            global project
            project = CaptureProject(value)
        elif isinstance(value, dict):
            for inner_key, inner_value in value:
                spreads.config[key][inner_key] = inner_value
        else:
            spreads.config[key] = value


def _get_configuration():
    ext_keys = common.get_relevant_extensions(('prepare_capture', 'capture',
                                               'finish_capture', 'download'))
    our_keys = ('download', 'dpi') + tuple(ext_keys)
    config = spreads.config.flatten()
    out_dict = {k: v for k, v in config.iteritems() if k in our_keys}
    out_dict.update({'project_name': project.name})
    return out_dict


@scan_api.route('/messages')
def get_log():
    # TODO: Use message flashing functions for this?
    # TODO: Return last 100 >=INFO logging messages
    raise NotImplementedError


@scan_api.route('/')
def get_status():
    try:
        status = {'current_step': project.current_step,
                  'devices_locked': project.devices_locked,
                  'devices_prepared': project.devices_prepared,
                  }
        return jsonify(status=status)
    except AttributeError:
        abort(HTTP_STATUS_CODES['Precondition Required'])


@scan_api.route('/configuration', methods=['GET', 'POST'])
def configuration():
    if request.method == 'POST':
        _set_configuration(request.get_json())
    else:
        return jsonify(_get_configuration())


@scan_api.route('/configuration/template', methods=['GET'])
def get_configuration_template():
    tmpl = common.get_configuration_template(
        hooks=('prepare_capture', 'capture', 'finish_capture',
               'download')
    )
    return jsonify(tmpl)


@scan_api.route('/capture/prepare', methods=['POST'])
def prepare_capture():
    global current_step
    if project.devices_prepared:
        return
    if project.devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    current_step = 'prepare'
    with lock_devices():
        workflow.prepare_capture(devices=devices)


@scan_api.route('/capture', methods=['GET'])
def capture():
    global current_step, time_first_capture, devices, number_captures
    if not project.devices_prepared:
        return make_response("The devices are not yet prepared.",
                             HTTP_STATUS_CODES['Precondition Required'])
    if project.devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    if not project.current_step == 'capture':
        current_step = 'capture'
        time_first_capture = time.time()
    with lock_devices():
        workflow.capture(devices=devices)
    project.number_captures += 1
    pages_per_hour = ((3600/(time.time() - time_first_capture))
                      * project.number_captures)
    return jsonify({'capture_number': project.number_captures,
                    'pages_per_hour': pages_per_hour})


@scan_api.route('/download', methods=['GET'])
def download(name):
    if project.devices_locked:
        abort(HTTP_STATUS_CODES['Locked'])
    elif project.download_thread is None:
        project.devices_locked = True
        project.download_thread = Thread(target=workflow.download,
                                         args=(devices, project.path))
        return
    elif project.download_thread.is_alive():
        return jsonify({'done': False})
    else:
        project.devices_locked = False
        project.download_thread = None
        return jsonify({'done': True})


@scan_api.route('/images', methods=['GET', 'POST', 'PATCH'])
def get_image_list(name):
    if request.method == 'GET':
        image_list = os.listdir(os.path.join(project.path, 'raw'))
        return jsonify(images=image_list)
    elif request.method == 'POST' or 'PATCH':
        # TODO: Get updated order from request
        # TODO: Apply changes to images
        raise NotImplementedError


@scan_api.route('/images/<img_name>', methods=['GET'])
def get_image(name, img_name):
    # TODO: Load image, return as image
    raise NotImplementedError


@scan_api.route('/images/<img_name>', methods=['DELETE'])
def delete_image(name, img_name):
    # TODO: Delete the image
    raise NotImplementedError


@scan_api.route('/capture/finish', methods=['GET'])
def finish_capture():
    global project
    project = CaptureProject()

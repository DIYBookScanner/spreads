# -*- coding: utf-8 -*-
from __future__ import division

import itertools
import logging
import logging.handlers
import subprocess
import sys
import traceback
from isbnlib import is_isbn10, is_isbn13

import pkg_resources
import requests
from flask import (json, jsonify, request, send_file, render_template,
                   redirect, make_response, Response)
from werkzeug.contrib.cache import SimpleCache

import spreads.metadata
import spreads.plugin as plugin
from spreads.util import is_os, get_version, DeviceException
from spreads.workflow import Workflow, ValidationError

from spreadsplug.web import app
from discovery import discover_servers
from util import WorkflowConverter, get_thumbnail, scale_image, convert_image

if is_os('windows'):
    from util import find_stick_win as find_stick
else:
    from util import find_stick

logger = logging.getLogger('spreadsplug.web')

# Simple dictionary-based cache for expensive calculations
cache = SimpleCache()

# Register custom workflow converter for URL routes
app.url_map.converters['workflow'] = WorkflowConverter


class ApiException(Exception):
    def __init__(self, message, status_code=500, payload=None,
                 error_type='general'):
        super(ApiException, self).__init__(message)
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.error_type = error_type

    def to_dict(self):
        return {
            'type': self.error_type,
            'payload': self.payload,
            'message': self.message
        }


@app.errorhandler(ValidationError)
def handle_validationerror(error):
    return handle_apiexception(ApiException(
        "There was an issue with at least some of the supplied values.",
        400, error.errors, 'validation'))


@app.errorhandler(ApiException)
def handle_apiexception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code or 500
    return response


@app.errorhandler(Exception)
def handle_general_exception(error):
    logger.exception(error)
    exc_type, exc, trace = sys.exc_info()
    response = jsonify({
        'message': error.message,
        'type': exc_type.__name__ if exc_type is not None else None,
        'traceback': traceback.format_tb(trace)
    })
    response.status_code = 500
    return response


# ========= #
#  General  #
# ========= #
@app.route('/')
def index():
    """ Deliver static landing page that launches the client-side app. """
    default_config = cache.get('default-config')
    if default_config is None:
        default_config = app.config['default_config'].flatten()
        cache.set('default-config', default_config)
    templates = cache.get('plugin-templates')
    if templates is None:
        templates = get_templates()
        cache.set('plugin-templates', templates)
    return render_template(
        "index.html",
        version=get_version(),
        debug=app.config['debug'],
        default_config=default_config,
        plugins=list_plugins(),
        config_templates=templates,
        metaschema=spreads.metadata.Metadata.SCHEMA,
    )


def list_plugins():
    config = app.config['default_config']
    plugins = plugin.get_plugins(*config['plugins'].get())
    return {
        'capture': [name for name, cls in plugins.iteritems()
                    if issubclass(cls, plugin.CaptureHooksMixin)],
        'trigger': [name for name, cls in plugins.iteritems()
                    if issubclass(cls, plugin.TriggerHooksMixin)],
        'postprocessing': [name for name, cls in plugins.iteritems()
                           if issubclass(cls, plugin.ProcessHookMixin)],
        'output': [name for name, cls in plugins.iteritems()
                   if issubclass(cls, plugin.OutputHookMixin)]
    }


def get_templates():
    plugins = list_plugins()
    config = app.config['default_config']
    if app.config['mode'] == 'scanner':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in plugins['capture'] or
                     section in plugins['trigger'] or
                     section in ('core', 'device', 'web')}
    elif app.config['mode'] == 'processor':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in plugins['postprocessing']
                     or section in ('core', 'web')}
    elif app.config['mode'] == 'full':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in itertools.chain(*plugins.values())
                     or section in ('core', 'device', 'web')}
    rv = dict()
    for plugname, options in templates.iteritems():
        if options is None:
            continue
        for key, option in options.iteritems():
            if option.selectable:
                value = [config[plugname][key].get()]
                value += [x for x in option.value if x not in value]
            else:
                value = config[plugname][key].get()
            if not plugname in rv:
                rv[plugname] = dict()
            rv[plugname][key] = dict(value=value,
                                     docstring=option.docstring,
                                     selectable=option.selectable,
                                     advanced=option.advanced,
                                     depends=option.depends)
    return rv


@app.route('/api/plugins')
def get_available_plugins():
    exts = list(pkg_resources.iter_entry_points('spreadsplug.hooks'))
    activated = app.config['default_config']['plugins'].get()
    post_plugins = sorted(
        [ext.name for ext in exts if ext.name in activated
         and issubclass(ext.load(), plugin.ProcessHookMixin)],
        key=lambda x: activated.index(x))
    return jsonify({
        'postprocessing': post_plugins,
        'output': [ext.name for ext in exts if ext.name in activated
                   and issubclass(ext.load(), plugin.OutputHookMixin)]
    })


@app.route('/api/templates')
def template_endpoint():
    return jsonify(get_templates())


@app.route("/api/config", methods=['GET'])
def get_default_config():
    default_config = cache.get('default-config')
    if default_config is None:
        default_config = app.config['default_config'].flatten()
        cache.set('default-config', default_config)
    return jsonify(default_config)


@app.route("/api/config", methods=['PUT'])
def update_default_config():
    current = app.config['default_config']
    new_values = json.loads(request.data)
    current._config.set(new_values)
    current.dump(current.cfg_path)
    if "core" in new_values or "web" in new_values:
        import tornado.autoreload as autoreload
        autoreload._reload()
    return ""


def check_submit_allowed():
    if app.config['mode'] != 'scanner':
        raise ApiException("Action only possible when running in 'scanner'"
                           " mode.", 503)


@app.route('/api/remote/discover')
def discover_postprocessors():
    check_submit_allowed()
    servers = discover_servers()
    if app.config['postprocessing_server']:
        servers.append(app.config['postprocessing_server'].split(':'))
    return jsonify(servers=["{0}:{1}".format(*addr) for addr in servers])


def get_from_remote_server(server, endpoint):
    try:
        resp = requests.get('http://' + server + endpoint)
    except requests.ConnectionError:
        raise ValidationError(
            server="Could not reach server at supplied address.")
    return resp.content, resp.status_code


@app.route('/api/remote/plugins')
def get_remote_plugins():
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    check_submit_allowed()
    data, status = get_from_remote_server(request.args.get("server"),
                                          '/api/plugins')
    return make_response(data, status, {'Content-Type': 'application/json'})


@app.route('/api/remote/templates')
def get_remote_templates():
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    check_submit_allowed()
    data, status = get_from_remote_server(request.args.get("server"),
                                          '/api/templates')
    return make_response(data, status, {'Content-Type': 'application/json'})


@app.route('/api/remote/config')
def get_remote_config():
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    check_submit_allowed()
    data, status = get_from_remote_server(request.args.get("server"),
                                          '/api/config')
    return make_response(data, status, {'Content-Type': 'application/json'})


@app.route('/api/log')
def get_logs():
    start = int(request.args.get('start', '0'))
    count = int(request.args.get('count', '50'))
    level = request.args.get('level', 'INFO')
    logbuffer = next(
        x for x in logging.getLogger().handlers
        if isinstance(x, logging.handlers.BufferingHandler)).buffer
    available_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if level.upper() not in available_levels:
        levels = available_levels[available_levels.index('INFO'):]
    else:
        levels = available_levels[available_levels.index(level.upper()):]
    msgs = [msg for msg in sorted(logbuffer, key=lambda x: x.relativeCreated,
                                  reverse=True)
            if msg.levelname in levels]
    return jsonify(total_num=len(msgs),
                   messages=msgs[start:start+count])


@app.route('/api/isbn')
def query_isbn():
    query = request.args.get('q')
    if query:
        return jsonify(results=spreads.metadata.get_isbn_suggestions(query))
    else:
        raise ValidationError(q='Missing parameter')


@app.route('/api/isbn/<isbn>')
def get_isbn_info(isbn):
    if isbn.lower().startswith('isbn:'):
        isbn = isbn[5:]
    is_isbn = is_isbn10(isbn) or is_isbn13(isbn)
    if not is_isbn:
        raise ValidationError(isbn='Not a valid ISBN.')
    match = spreads.metadata.get_isbn_metadata(isbn)
    if match:
        return jsonify(match)
    else:
        raise ValidationError(isbn='Could not find match for ISBN.')


# ================== #
#  Workflow-related  #
# ================== #
@app.route('/api/workflow', methods=['POST'])
def create_workflow():
    """ Create a new workflow.

    Returns the newly created workflow as a JSON object.
    """
    data = json.loads(request.data)

    if data.get('config'):
        config = app.config['default_config'].with_overlay(
            data.get('config'))
    else:
        config = app.config['default_config']

    metadata = data.get('metadata', {})

    workflow = Workflow.create(location=app.config['base_path'],
                               config=config,
                               metadata=metadata)
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow', methods=['GET'])
def list_workflows():
    """ Return a list of all workflows. """
    workflows = Workflow.find_all(app.config['base_path'])
    return make_response(json.dumps(workflows.values()),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['GET'])
def get_workflow(workflow):
    """ Return a single workflow. """
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['PUT'])
def update_workflow(workflow):
    """ Update a single workflow.

    Payload should be a JSON object, as returned by the '/workflow/<id>'
    endpoint.
    Currently the only attributes that can be updated from the client
    are `config` and `metadata`.

    Returns the updated workflow as a JSON object.
    """
    data = json.loads(request.data)
    config = data.get('config')
    metadata = data.get('metadata')
    # Update workflow configuration
    if config:
        workflow.update_configuration(config)
    # Update metadata
    if metadata:
        workflow.metadata = metadata
    # Persist to disk
    workflow.save()
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['DELETE'])
def delete_workflow(workflow):
    """ Delete a single workflow from database and disk. """
    Workflow.remove(workflow)
    return jsonify({})


@app.route('/api/workflow/<workflow:workflow>/download', methods=['GET'])
def download_workflow(workflow):
    """ Redirect to download endpoint (see __init__.py) with proper filename
    set.
    """
    archive_format = request.args.get('fmt', 'tar')
    if archive_format not in ('zip', 'tar'):
        raise ValidationError(fmt='Must be zip or tar.')
    fname = "{0}.{1}".format(workflow.path.stem, archive_format)
    return redirect('/api/workflow/{0}/download/{1}'.format(
                    workflow.id, fname))


@app.route('/api/workflow/<workflow:workflow>/transfer', methods=['POST'])
def transfer_workflow(workflow):
    """ Transfer workflow to an attached USB storage device.

    """
    try:
        stick = find_stick()
    except ImportError:
        raise ApiException(
            "The transfer feature requires that the `python-dbus` module is "
            "installed on the system.", error_type='transfer')
    if stick is None:
        raise ApiException(
            "Could not find a removable devices to transfer to."
            "If you have connected one, make sure that it is formatted with "
            "the FAT32 file system", 503, error_type='transfer')
    from tasks import transfer_to_stick
    transfer_to_stick(workflow.id, app.config['base_path'])
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/submit', methods=['POST'])
def submit_workflow(workflow):
    """ Submit the requested workflow to the postprocessing server.
    """
    check_submit_allowed()
    data = json.loads(request.data)
    server = data.get('server')
    if not server:
        raise ValidationError(server="required")
    user_config = data.get('config', {})
    from tasks import upload_workflow
    upload_workflow(workflow.id, app.config['base_path'],
                    'http://{0}/api/workflow/upload'.format(server),
                    user_config,
                    start_process=data.get('start_process', False),
                    start_output=data.get('start_output', False))
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/output/<fname>')
def get_output_file(workflow, fname):
    try:
        fpath = next(fp for fp in workflow.out_files if fp.name == fname)
    except StopIteration:
        raise ApiException("Could not find file with name '{0}' amongst "
                           "output files for workflow '{1}'"
                           .format(fname, workflow.id), 404)
    return send_file(unicode(fpath))


# =============== #
#  Page-related  #
# =============== #
def find_page(workflow, number):
    page = next((p for p in workflow.pages if p.capture_num == number), None)
    if not page:
        raise ApiException("Could not find page with capture number {1}"
                           .format(number), 404)
    return page


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>')
def get_single_page(workflow, number):
    page = find_page(workflow, number)
    return jsonify(dict(page=page))


@app.route('/api/workflow/<workflow:workflow>/page')
def get_all_pages(workflow):
    return make_response(json.dumps(workflow.pages),
                         200, {'Content-Type': 'application/json'})


def check_page_params(page, img_type, plugname):
    if img_type not in ('raw', 'processed'):
        raise ValidationError(
            route=("Image type must be one of 'raw' or 'processed' (was {0})"
                   .format(img_type)))
    if plugname is not None and plugname not in page.processed_images:
        raise ApiException("No processed file present for plugin '{0}'"
                           .format(plugname))


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>',
           defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>'
           '/<plugname>')
def get_page_image(workflow, number, img_type, plugname):
    """ Return image for requested page. """
    # Scale image if requested
    width = request.args.get('width', None)
    img_format = request.args.get('format', None)
    page = find_page(workflow, number)
    check_page_params(page, img_type, plugname)
    if img_type == 'raw':
        fpath = page.raw_image
    elif plugname is None:
        fpath = page.get_latest_processed(image_only=True)
    else:
        fpath = page.processed_images[plugname]
    if width and fpath.suffix.lower() in ('.jpg', '.jpeg', '.tif', '.tiff',
                                          '.png'):
        return scale_image(fpath, width=int(width))
    elif fpath.suffix.lower() in ('.tif', '.tiff') and img_format:
        img_format = 'png' if img_format == 'browser' else img_format
        return convert_image(fpath, img_format)
    else:
        return send_file(unicode(fpath))


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/'
           'thumb', defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/'
           '<plugname>/thumb', methods=['GET'])
def get_page_image_thumb(workflow, number, img_type, plugname):
    """ Return thumbnail for page image from requested workflow. """
    page = find_page(workflow, number)
    check_page_params(page, img_type, plugname)
    if img_type == 'raw':
        fpath = page.raw_image
    elif plugname is None:
        fpath = page.get_latest_processed(image_only=True)
    else:
        fpath = page.processed_images[plugname]
    if fpath.suffix.lower() not in ('.jpg', '.jpeg', '.tif', '.tiff', '.png'):
        raise ApiException("Can not serve thumbnails for files with type {0}"
                           .format(fpath.suffix), 500)
    cache_key = "{0}.{1}.{2}".format(workflow.id, img_type, fpath.name)
    thumbnail = None
    if not request.args:
        thumbnail = cache.get(cache_key)
    if thumbnail is None:
        thumbnail = get_thumbnail(fpath)
        cache.set(cache_key, thumbnail)
    return Response(thumbnail, mimetype='image/jpeg')


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>',
           methods=['DELETE'])
def delete_page(workflow, number):
    """ Remove a single page from a workflow. """
    page = find_page(workflow, number)
    workflow.remove_pages(page)
    return jsonify(dict(page=page))


@app.route(
    '/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/crop',
    methods=['POST'])
def crop_workflow_image(workflow, number, img_type):
    # TODO: We have to update the checksum!
    page = find_page(workflow, number)
    if img_type != 'raw':
        raise ApiException("Can only crop raw images.", 400)
    left = int(request.args.get('left', 0))
    top = int(request.args.get('top', 0))
    width = int(request.args.get('width', 0)) or None
    height = int(request.args.get('height', 0)) or None
    workflow.crop_page(page, left, top, width, height, async=True)
    cache_key = "{0}.{1}.{2}".format(workflow.id, 'raw', page.raw_image.name)
    cache.delete(cache_key)
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/page', methods=['DELETE'])
def bulk_delete_pages(workflow):
    cap_nums = [p['capture_num'] for p in json.loads(request.data)['pages']]
    to_delete = [p for p in workflow.pages if p.capture_num in cap_nums]
    logger.debug("Bulk removing from workflow {0}: {1}".format(
        workflow.id, to_delete))
    workflow.remove_pages(*to_delete)
    return make_response(json.dumps(to_delete),
                         200, {'Content-Type': 'application/json'})


# ================= #
#  Capture-related  #
# ================= #
def check_capture_allowed():
    if app.config['mode'] not in ('scanner', 'full'):
        raise ApiException("Only possible when running in 'scanner' or 'full'"
                           " mode.", 503)


@app.route('/api/workflow/<workflow:workflow>/prepare_capture',
           methods=['POST'])
def prepare_capture(workflow):
    """ Prepare capture for the requested workflow.

    """
    check_capture_allowed()
    # Check if any other workflow is active and finish, if neccessary
    logger.debug("Finishing previous workflows")
    wfitems = Workflow.find_all(app.config['base_path'], key='id').iteritems()
    for wfid, wf in wfitems:
        if wf.status['step'] == 'capture' and wf.status['prepared']:
            if wf is workflow and not request.args.get('reset'):
                return 'OK'
            wf.finish_capture()
    try:
        workflow.prepare_capture()
    except DeviceException as e:
        logger.error(e)
        raise ApiException("Could not prepare capture: {0}".format(e.message),
                           500, error_type='device')
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/capture', methods=['POST'])
def trigger_capture(workflow):
    """ Trigger a capture on the requested workflow.

    Optional parameter 'retake' specifies if the last shot is to be retaken.

    Returns the number of pages shot and a list of the pages captured by
    this call in JSON notation.
    """
    check_capture_allowed()
    status = workflow.status
    if status['step'] != 'capture' or not status['prepared']:
        workflow.prepare_capture()
    try:
        workflow.capture(retake=('retake' in request.args))
    except IOError as e:
        logger.error(e)
        raise ApiException("Could not capture images: {0}"
                           .format(e.message), 500)
    except DeviceException as e:
        logger.error(e)
        raise ApiException("Could not capture image: {0}"
                           .format(e.message), 500, error_type='device')
    return jsonify({
        'pages_shot': len(workflow.pages),
        'pages': workflow.pages[-2:]
    })


@app.route('/api/workflow/<workflow:workflow>/finish_capture',
           methods=['POST'])
def finish_capture(workflow):
    """ Wrap up capture process on the requested workflow. """
    check_capture_allowed()
    workflow.finish_capture()
    return 'OK'


def check_processing_allowed():
    if app.config['mode'] not in ('processor', 'full'):
        raise ApiException("Only possible when running in 'processor' or"
                           " 'full' mode.", 503)


@app.route('/api/workflow/<workflow:workflow>/process', methods=['POST'])
def start_processing(workflow):
    check_processing_allowed()
    workflow._update_status(step='process', step_progress=None)
    from tasks import process_workflow
    process_workflow(workflow.id, app.config['base_path'])
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/output', methods=['POST'])
def start_output_generation(workflow):
    check_processing_allowed()
    workflow._update_status(step='output', step_progress=None)
    from tasks import output_workflow
    output_workflow(workflow.id, app.config['base_path'])
    return 'OK'


# ================== #
#   System-related   #
# ================== #
def check_for_standalone_mode():
    if not app.config['standalone']:
        raise ApiException("Only available when server is run in standalone "
                           "mode", 503)


@app.route('/api/system/shutdown', methods=['POST'])
def shutdown():
    check_for_standalone_mode()
    logger.info("Shutting device down")
    try:
        subprocess.check_call("/usr/bin/sudo -n /sbin/shutdown -h now".split())
    except (subprocess.CalledProcessError, OSError):
        raise ApiException("The user running the server process needs to have "
                           "permission to run /sbin/shutdown via sudo.", 500)
    return ''


@app.route('/api/system/reboot', methods=['POST'])
def reboot():
    check_for_standalone_mode()
    try:
        subprocess.check_call("/usr/bin/sudo -n /sbin/shutdown -r now".split())
    except (subprocess.CalledProcessError, OSError):
        raise ApiException("The user running the server process needs to have "
                           "permission to run /sbin/shutdown via sudo.", 500)
    return ''


@app.route('/api/reset', methods=['POST'])
def reset():
    """ Restart the application. """
    # NOTE: This endpoint will never send a response, clients should take this
    #       into account and set a low timeout value.
    import tornado.autoreload as autoreload
    autoreload._reload()


@app.route('/<path:path>')
def redirect_pushstate(path):
    return redirect("/#{0}".format(path))

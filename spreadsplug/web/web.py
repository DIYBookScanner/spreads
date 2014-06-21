from __future__ import division

import copy
import itertools
import logging
import logging.handlers
import os
import StringIO
import subprocess
import time
import zipfile
from collections import deque

import blinker
import pkg_resources
import requests
from flask import (abort, json, jsonify, request, send_file, render_template,
                   url_for, redirect, make_response, Response)
from jpegtran import JPEGImage
from werkzeug.contrib.cache import SimpleCache

import spreads.plugin as plugin
from spreads.util import get_next
from spreads.workflow import Workflow, ValidationError

from spreadsplug.web import app
from discovery import discover_servers
from util import (WorkflowConverter, get_thumbnail, find_stick, scale_image,
                  convert_image)

logger = logging.getLogger('spreadsplug.web')

signals = blinker.Namespace()
on_download_prepared = signals.signal('download:prepared')
on_download_finished = signals.signal('download:finished')

# Event Queue for polling endpoints
event_queue = deque(maxlen=2048)

# Simple dictionary-based cache for expensive calculations
cache = SimpleCache()

# Register custom workflow converter for URL routes
app.url_map.converters['workflow'] = WorkflowConverter


class ApiException(Exception):
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(ApiException)
def handle_apiexception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
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
        templates = get_plugin_templates()
        cache.set('plugin-templates', templates)
    return render_template(
        "index.html",
        debug=app.config['DEBUG'],
        default_config=default_config,
        plugin_templates=templates
    )


def get_plugin_templates():
    """ Return the names of all globally activated plugins and their
        configuration templates.
    """
    config = app.config['default_config']
    plugins = plugin.get_plugins(*config['plugins'].get())
    scanner_exts = [name for name, cls in plugins.iteritems()
                    if any(issubclass(cls, mixin) for mixin in
                           (plugin.CaptureHooksMixin,
                            plugin.TriggerHooksMixin))]
    processor_exts = [name for name, cls in plugins.iteritems()
                      if any(issubclass(cls, mixin) for mixin in
                             (plugin.ProcessHookMixin,
                              plugin.OutputHookMixin))]
    if app.config['mode'] == 'scanner':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in scanner_exts or section == 'device'}
    elif app.config['mode'] == 'processor':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in processor_exts}
    elif app.config['mode'] == 'full':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section != 'core'}
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
                                     advanced=option.advanced)
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


@app.route('/api/plugins/templates')
def template_endpoint():
    return jsonify(get_plugin_templates())


@app.route('/api/remote/discover')
def discover_postprocessors():
    if app.config['mode'] != 'scanner':
        raise ApiException("Discovery only possible when running in 'scanner'"
                           " mode.", 503)
    servers = discover_servers()
    if app.config['postproc_server']:
        servers.append(app.config['postproc_server'].split(':'))
    return jsonify(servers=["{0}:{1}".format(*addr) for addr in servers])


@app.route('/api/remote/plugins')
def get_remote_plugins():
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    if app.config['mode'] != 'scanner':
        raise ApiException("Submission only possible when running in 'scanner'"
                           " mode.", 503)
    server = request.args.get("server")
    if not server:
        raise ApiException("Missing 'server' parameter", 400)
    try:
        resp = requests.get('http://{0}/api/plugins'.format(server))
    except requests.ConnectionError:
        resp = False
    if not resp:
        errors = {'server': 'Could not reach server at supplied address.'}
        return make_response(json.dumps(dict(errors=errors)), 400,
                             {'Content-Type': 'application/json'})
    else:
        return make_response(resp.content, resp.status_code,
                             {'Content-Type': 'application/json'})


@app.route('/api/remote/plugins/templates')
def get_remote_templates():
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    if app.config['mode'] != 'scanner':
        raise ApiException("Submission only possible when running in 'scanner'"
                           " mode.", 503)
    server = request.args.get("server")
    if not server:
        raise ApiException("Missing 'server' parameter", 400)
    try:
        resp = requests.get('http://{0}/api/plugins/templates'.format(server))
    except requests.ConnectionError:
        resp = False
    if not resp:
        errors = {'server': 'Could not reach server at supplied address.'}
        return make_response(json.dumps(dict(errors=errors)), 400,
                             {'Content-Type': 'application/json'})
    else:
        return make_response(resp.content, resp.status_code,
                             {'Content-Type': 'application/json'})


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


# ================== #
#  Workflow-related  #
# ================== #
@app.route('/api/workflow', methods=['POST'])
def create_workflow():
    """ Create a new workflow.

    Payload should be a JSON object. The only required attribute is 'name' for
    the desired workflow name. Optionally, 'config' can be set to a
    configuration object in the form "plugin_name: { setting: value, ...}".

    Returns the newly created workflow as a JSON object.
    """
    if request.content_type == 'application/zip':
        zfile = zipfile.ZipFile(StringIO.StringIO(request.data))
        zfile.extractall(path=app.config['base_path'])
        wfname = os.path.dirname(zfile.filelist[0].filename)
        workflow = Workflow(path=os.path.join(app.config['base_path'], wfname))
        from spreads.workflow import on_created
        on_created.send(workflow, workflow=workflow)
    else:
        data = json.loads(request.data)

        if data.get('config'):
            config = app.config['default_config'].with_overlay(
                data.get('config'))
        else:
            config = app.config['default_config']

        metadata = data.get('metadata', {})

        try:
            workflow = Workflow.create(location=app.config['base_path'],
                                       name=unicode(data['name']),
                                       config=config,
                                       metadata=metadata)
        except ValidationError as e:
            return make_response(json.dumps(dict(errors=e.errors)), 400,
                                 {'Content-Type': 'application/json'})
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
    Currently the only attribute that can be updated from the client
    is the configuration.

    Returns the updated workflow as a JSON object.
    """
    # TODO: Support renaming a workflow, i.e. rename directory as well
    data = json.loads(request.data)
    name = data.get('name')
    if workflow.path.name != name:
        new_path = workflow.path.parent/name
        workflow.path.rename(new_path)
        workflow.path = new_path
    config = data.get('config')
    # Update workflow configuration
    workflow.update_configuration(config)
    # Persist to disk
    workflow.save()
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['DELETE'])
def delete_workflow(workflow):
    """ Delete a single workflow from database and disk. """
    Workflow.remove(workflow)
    return jsonify({})


@app.route('/api/events', methods=['GET'])
def get_events():
    """ Get a list of all events that were emitted on the server.

    :param int count:   Number of events to return, default is all in the queue
    :param float since: Only return events that were emitted after the
                        (epoch) timestamp
    """
    count = request.args.get('count', None, int)
    since = request.args.get('since', None, float)
    events = None
    if count:
        events = tuple(itertools.islice(reversed(event_queue), count))[::-1]
    elif since is not None:
        events = tuple(event for event in event_queue
                       if event.emitted > since)
    else:
        events = tuple(event_queue)
    return make_response(
        json.dumps(events),
        200, {'Content-Type': 'application/json'})


@app.route('/api/poll', methods=['GET'])
def poll_for_events():
    """ Wait for events to be emitted on the server.

    If there is a `last_polled` field in the request cookie, it will return
    all events that were emitted since that timestamp. This ensures that no
    events will be missed in a long-polling scenario.
    """
    events = None
    start_time = time.time()
    last_polled = request.cookies.get('last_polled', start_time, float)
    # Only record debug logging events when the app is running in
    # debug mode
    if app.config['DEBUG']:
        skip = lambda event: (
            event.signal.name == 'logrecord'
            and event.data['record'].levelno == logging.DEBUG)
    else:
        skip = lambda event: False
    while time.time() - start_time < 35:
        # NOTE: We need to iterate over a copy of the event queue, since
        #       it might change its content while we iterate
        events = tuple(event for event in copy.copy(event_queue)
                       if event.emitted > last_polled and not skip(event))
        if events:
            resp = make_response(
                json.dumps(events),
                200, {'Content-Type': 'application/json'})
            resp.set_cookie('last_polled', str(events[-1].emitted))
            return resp
        else:
            time.sleep(.1)
    abort(408)  # Request Timeout


@app.route('/api/workflow/<workflow:workflow>/download', methods=['GET'],
           defaults={'fname': None})
@app.route('/api/workflow/<workflow:workflow>/download/<fname>',
           methods=['GET'])
def download_workflow(workflow, fname):
    """ Return a ZIP archive of the current workflow.

    Included all files from the workflow folder as well as the workflow
    configuration as a YAML dump.
    """
    # Set proper file name for zip file
    if fname is None:
        return redirect(url_for('download_workflow', workflow=workflow,
                        fname="{0}.zip".format(workflow.path.stem)))

    zstream = workflow.bag.package_as_zipstream(compression=None)
    zstream_copy = copy.deepcopy(zstream)
    zipsize = sum(len(data) for data in zstream_copy)
    on_download_prepared.send(workflow)

    def zstream_wrapper():
        """ Wrapper around our zstream so we can emit a signal when all data
        has been streamed to the client.
        """
        for data in zstream:
            yield data
        on_download_finished.send()

    response = Response(zstream_wrapper(), mimetype='application/zip')
    response.headers['Content-length'] = int(zipsize)
    return response


@app.route('/api/workflow/<workflow:workflow>/transfer', methods=['POST'])
def transfer_workflow(workflow):
    """ Transfer workflow to an attached USB storage device.

    """
    try:
        stick = find_stick()
    except ImportError:
        return jsonify({"error": "Missing package 'python-dbus', "
                                 "please install."})
    if stick is None:
        return jsonify({"error": "Could not find removable device"}), 503
    from tasks import transfer_to_stick
    transfer_to_stick(workflow.id, app.config['base_path'])
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/submit', methods=['POST'])
def submit_workflow(workflow):
    """ Submit the requested workflow to the postprocessing server.

    Only available in 'scanner' mode. Requires that the 'postproc_server'
    option is set to the address of a server with the server in 'processor'
    or 'full' mode running.
    """
    if app.config['mode'] != 'scanner':
        raise ApiException("Submission only possible when running in 'scanner'"
                           " mode.", 503)
    data = json.loads(request.data)
    server = data.get('server')
    if not server:
        raise ApiException("Missing 'server' field in JSON data", 400)
    user_config = data.get('config', {})
    from tasks import upload_workflow
    # TODO: Pass config to this function
    upload_workflow(workflow.id, app.config['base_path'],
                    'http://{0}/api/workflow'.format(server), user_config,
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
@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>')
def get_single_page(workflow, seq_num):
    page = get_next(p for p in workflow.pages if p.sequence_num == seq_num)
    if not page:
        raise ApiException("Could not find page with sequence number {0}"
                           .format(seq_num), 404)
    return jsonify(page)


@app.route('/api/workflow/<workflow:workflow>/page')
def get_all_pages(workflow):
    return make_response(json.dumps(workflow.pages),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>/<img_type>',
           defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>/<img_type>'
           '/<plugname>')
def get_page_image(workflow, seq_num, img_type, plugname):
    """ Return image for requested page. """
    if img_type not in ('raw', 'processed'):
        raise ApiException("Image type must be one of 'raw' or 'processed', "
                           "not '{0}'".format(img_type), 400)
    # Scale image if requested
    width = request.args.get('width', None)
    img_format = request.args.get('format', None)
    page = get_next(p for p in workflow.pages if p.sequence_num == seq_num)
    if not page:
        raise ApiException("Could not find page with sequence number {0}"
                           .format(seq_num), 404)
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


@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>/<img_type>/'
           'thumb', defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>/<img_type>/'
           '<plugname>/thumb', methods=['GET'])
def get_page_image_thumb(workflow, seq_num, img_type, plugname):
    """ Return thumbnail for page image from requested workflow. """
    if img_type not in ('raw', 'processed'):
        raise ApiException("Image type must be one of 'raw' or 'processed', "
                           "not '{0}'".format(img_type), 400)
    if img_type == 'processed' and plugname is None:
        raise ApiException("Need to supply additional path parameter for "
                           "plugin to get processed file for.", 400)
    page = get_next(p for p in workflow.pages if p.sequence_num == seq_num)
    if not page:
        raise ApiException("Could not find page with sequence number {0}"
                           .format(seq_num), 404)
    if img_type == 'raw':
        fpath = page.raw_image
    elif plugname is None:
        fpath = page.get_latest_processed(image_only=True)
    else:
        fpath = page.processed_images[plugname]
    if fpath.suffix.lower() not in ('.jpg', '.jpeg', '.tif', '.tiff', '.png'):
        raise ApiException("Can not serve thumbnails for files with type {0}"
                           .format(fpath.suffix), 400)
    cache_key = "{0}.{1}.{2}".format(workflow.id, img_type, fpath.name)
    thumbnail = None
    if not request.args:
        thumbnail = cache.get(cache_key)
    if thumbnail is None:
        thumbnail = get_thumbnail(fpath)
        cache.set(cache_key, thumbnail)
    return Response(thumbnail, mimetype='image/jpeg')


@app.route('/api/workflow/<workflow:workflow>/page/<int:seq_num>',
           methods=['DELETE'])
def delete_page(workflow, seq_num):
    """ Remove a single page from a workflow. """
    page = get_next(p for p in workflow.pages if p.sequence_num == seq_num)
    if not page:
        raise ApiException("Could not find page with sequence number {0}"
                           .format(seq_num), 404)
    workflow.remove_pages(page)
    return jsonify(page)


@app.route(
    '/api/workflow/<workflow:workflow>/page/<int:seq_num>/<img_type>/crop',
    methods=['POST'])
def crop_workflow_image(workflow, seq_num, img_type):
    # TODO: Shouldn't this be a method in Workflow?
    # TODO: We have to update the checksum!
    page = get_next(p for p in workflow.pages if p.sequence_num == seq_num)
    if not page:
        raise ApiException("Could not find page with sequence number {0}"
                           .format(seq_num), 404)
    if img_type != 'raw':
        raise ApiException("Can only crop raw images.", 400)
    img = JPEGImage(unicode(page.raw_image))
    params = {
        'x': int(request.args.get('left', 0)),
        'y': int(request.args.get('top', 0)),
    }
    width = int(request.args.get('width', img.width - params['x']))
    height = int(request.args.get('height', img.height - params['y']))
    if width > img.width:
        width = img.width
    if height > img.height:
        width = img.height
    params['width'] = width
    params['height'] = height
    logger.debug("Cropping \"{0}\" to x:{1} y:{2} w:{3} h:{4}"
                 .format(page.raw_image, *params.values()))
    cropped = img.crop(**params)
    cropped.save(unicode(page.raw_image))
    cache_key = "{0}.{1}.{2}".format(workflow.id, 'raw', page.raw_image.name)
    cache.delete(cache_key)
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/page', methods=['DELETE'])
def bulk_delete_pages(workflow):
    seq_nums = [p['sequence_num'] for p in json.loads(request.data)['pages']]
    to_delete = [p for p in workflow.pages if p.sequence_num in seq_nums]
    logger.debug("Bulk removing from workflow {0}: {1}".format(
        workflow.id, to_delete))
    workflow.remove_pages(*to_delete)
    return make_response(json.dumps(to_delete),
                         200, {'Content-Type': 'application/json'})


# ================= #
#  Capture-related  #
# ================= #
@app.route('/api/workflow/<workflow:workflow>/prepare_capture',
           methods=['POST'])
def prepare_capture(workflow):
    """ Prepare capture for the requested workflow.

    """
    if app.config['mode'] not in ('scanner', 'full'):
        raise ApiException("Only possible when running in 'scanner' or 'full'"
                           " mode.", 503)

    # Check if any other workflow is active and finish, if neccessary
    logger.debug("Finishing previous workflows")
    wfitems = Workflow.find_all(app.config['base_path'], key='id').iteritems()
    for wfid, wf in wfitems:
        if wf.status['step'] == 'capture' and wf.status['prepared']:
            if wf is workflow and not request.args.get('reset'):
                return 'OK'
            wf.finish_capture()
    workflow.prepare_capture()
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/capture', methods=['POST'])
def trigger_capture(workflow):
    """ Trigger a capture on the requested workflow.

    Optional parameter 'retake' specifies if the last shot is to be retaken.

    Returns the number of pages shot and a list of the pages captured by
    this call in JSON notation.
    """
    if app.config['mode'] not in ('scanner', 'full'):
        raise ApiException("Only possible when running in 'scanner' or 'full'"
                           " mode.", 503)
    status = workflow.status
    if status['step'] != 'capture' or not status['prepared']:
        # TODO: Abort with error, since capture has to be prepared first
        workflow.prepare_capture()
    try:
        workflow.capture(retake=('retake' in request.args))
    except IOError as e:
        logger.error(e)
        raise ApiException("Error during capture: {0}".format(e.message), 500)
    return jsonify({
        'pages_shot': len(workflow.pages),
        'pages': workflow.pages[-2:]
    })


@app.route('/api/workflow/<workflow:workflow>/finish_capture',
           methods=['POST'])
def finish_capture(workflow):
    """ Wrap up capture process on the requested workflow. """
    if app.config['mode'] not in ('scanner', 'full'):
        raise ApiException("Only possible when running in 'scanner' or 'full'"
                           " mode.", 503)
    workflow.finish_capture()
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/process', methods=['POST'])
def start_processing(workflow):
    if app.config['mode'] not in ('processor', 'full'):
        raise ApiException("Only possible when running in 'processor' or"
                           " 'full' mode.", 503)
    from tasks import process_workflow
    process_workflow(workflow.id, app.config['base_path'])
    workflow._update_status(step='process', step_progress=None)
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/output', methods=['POST'])
def start_output_generation(workflow):
    if app.config['mode'] not in ('processor', 'full'):
        raise ApiException("Only possible when running in 'processor' or"
                           " 'full' mode.", 503)
    from tasks import output_workflow
    output_workflow(workflow.id, app.config['base_path'])
    workflow._update_status(step='output', step_progress=None)
    return 'OK'


# ================== #
#   System-related   #
# ================== #
@app.route('/api/system/shutdown', methods=['POST'])
def shutdown():
    if not app.config['standalone']:
        abort(503)
    # NOTE: This requires that the user running spreads can execute
    #       /sbin/shutdown via sudo.
    logger.info("Shutting device down")
    subprocess.call("/usr/bin/sudo /sbin/shutdown -h now".split())
    return ''


@app.route('/<path:path>')
def redirect_pushstate(path):
    return redirect("/#{0}".format(path))

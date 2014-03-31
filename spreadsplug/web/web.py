import json
import logging
import logging.handlers
import shutil
import subprocess
import time

import requests
import zipstream
from flask import (abort, json, jsonify, request, send_file, render_template,
                   url_for, redirect, make_response, Response)
from werkzeug import secure_filename
from werkzeug.contrib.cache import SimpleCache

import spreads.plugin as plugin
from spreads.vendor.pathlib import Path
from spreads.workflow import Workflow

import persistence
from spreadsplug.web import app
from util import (get_image_url, WorkflowConverter,
                  get_thumbnail, find_stick, scale_image)

logger = logging.getLogger('spreadsplug.web')


# Register custom workflow converter for URL routes
app.url_map.converters['workflow'] = WorkflowConverter


# ========= #
#  General  #
# ========= #
@app.route('/')
def index():
    """ Deliver static landing page that launches the client-side app. """
    return render_template(
        "index.html",
        debug=app.config['DEBUG'],
        default_config=app.config['default_config'].flatten(),
        plugin_templates=get_plugin_templates()
    )


def get_plugin_templates():
    """ Return the names of all globally activated plugins and their
        configuration templates.
    """
    config = app.config['default_config']
    pluginmanager = plugin.get_pluginmanager(config)
    scanner_extensions = [plugin.CaptureHooksMixin, plugin.TriggerHooksMixin]
    processor_extensions = [plugin.ProcessHookMixin, plugin.OutputHookMixin]
    if app.config['mode'] == 'scanner':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in plugin.get_relevant_extensions(
                         pluginmanager, scanner_extensions)}
        templates["device"] = (plugin.get_driver(config["driver"].get())
                               .driver.configuration_template())
    elif app.config['mode'] == 'processor':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in plugin.get_relevant_extensions(
                         pluginmanager, processor_extensions)}
    elif app.config['mode'] == 'full':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in plugin.get_relevant_extensions(
                         pluginmanager,
                         scanner_extensions + processor_extensions)}
        templates["device"] = (plugin.get_driver(config["driver"].get())
                               .driver.configuration_template())
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
                                     selectable=option.selectable)
    return rv


@app.route('/log')
def get_logs():
    start = int(request.args.get('start', '0'))
    count = int(request.args.get('count', '50'))
    level = request.args.get('level', 'INFO')
    poll = 'poll' in request.args and request.args.get('poll') != 'false'
    logbuffer = next(
        x for x in logging.getLogger().handlers
        if isinstance(x, logging.handlers.BufferingHandler)).buffer
    available_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if level.upper() not in available_levels:
        levels = available_levels[available_levels.index('INFO'):]
    else:
        levels = available_levels[available_levels.index(level.upper()):]
    if not poll:
        msgs = get_log_lines(logbuffer=logbuffer, levels=levels)
        return jsonify(total_num=len(msgs),
                       messages=msgs[start:start+count])

    last_logtime = logbuffer[-1].created
    start_time = time.time()
    while (time.time() - start_time) < 35:
        if logbuffer[-1].created != last_logtime:
            msgs = get_log_lines(logbuffer=logbuffer,
                                 since=last_logtime,
                                 levels=levels)
            return jsonify(total_num=len(msgs),
                           messages=msgs)
        else:
            time.sleep(0.1)
    abort(408)


# ================== #
#  Workflow-related  #
# ================== #
@app.route('/workflow', methods=['POST'])
def create_workflow():
    """ Create a new workflow.

    Payload should be a JSON object. The only required attribute is 'name' for
    the desired workflow name. Optionally, 'config' can be set to a
    configuration object in the form "plugin_name: { setting: value, ...}".

    Returns the newly created workflow as a JSON object.
    """
    data = json.loads(request.data)
    path = Path(app.config['base_path'])/unicode(data['name'])

    # Setup default configuration
    config = app.config['default_config']
    # Overlay user-supplied values, if existant
    user_config = data.get('config', None)
    if user_config is not None:
        config.set(user_config)
    workflow = Workflow(config=config, path=path,
                        step=data.get('step', None),
                        step_done=data.get('step_done', None))
    workflow.id = persistence.save_workflow(workflow)
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/workflow', methods=['GET'])
def list_workflows():
    """ Return a list of all workflows. """
    workflows = persistence.get_all_workflows()
    return make_response(json.dumps(workflows.values()),
                         200, {'Content-Type': 'application/json'})


@app.route('/workflow/<workflow:workflow>', methods=['GET'])
def get_workflow(workflow):
    """ Return a single workflow. """
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/workflow/<workflow:workflow>', methods=['PUT'])
def update_workflow(workflow):
    """ Update a single workflow.

    Payload should be a JSON object, as returned by the '/workflow/<id>'
    endpoint.
    Currently the only attribute that can be updated from the client
    is the configuration.

    Returns the updated workflow as a JSON object.
    """
    # TODO: Support renaming a workflow, i.e. rename directory as well
    config = json.loads(request.data).get('config', None)
    # Update workflow configuration
    workflow.config.set(config)
    # Persist to disk
    persistence.update_workflow_config(workflow.id, workflow.config)
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/workflow/<workflow:workflow>', methods=['DELETE'])
def delete_workflow(workflow):
    """ Delete a single workflow from database and disk. """
    # Remove directory
    try:
        shutil.rmtree(unicode(workflow.path))
    except OSError:
        logger.warning("Workflow path {0} could not be removed"
                       .format(workflow.path))
    # Remove from database
    persistence.delete_workflow(workflow.id)
    return jsonify({})


@app.route('/poll', methods=['GET'])
def poll_for_updates():
    """ Stall until one of the workflows has changed or an error message
    or a warning was logged.

    Returns a JSON object with a field 'workflows', containing a list of all
    changed workflows and a field 'messages', containing all errors and
    warnings since the last poll.
    """
    logbuffer = next(
        x for x in logging.getLogger().handlers
        if isinstance(x, logging.handlers.BufferingHandler)).buffer

    get_props = lambda x: {k: v for k, v in x.__dict__.iteritems()
                           if not k[0] == '_'}
    old_workflows = {workflow.id: get_props(workflow)
                     for workflow in persistence.get_all_workflows().values()}

    last_logtime = logbuffer[-1].relativeCreated

    start_time = time.time()
    while (time.time() - start_time) < 35:
        updated_workflows = {workflow.id: get_props(workflow)
                             for workflow
                             in persistence.get_all_workflows().values()}
        workflows_updated = (updated_workflows != old_workflows)
        log_updated = (logbuffer[-1].relativeCreated > last_logtime)

        if workflows_updated:
            workflows = [workflow_to_dict(persistence.get_workflow(wfid))
                         for wfid in updated_workflows
                         if (wfid not in old_workflows) or
                            (old_workflows[wfid] != updated_workflows[wfid])]
            old_workflows = updated_workflows
            logger.debug("Workflows updated")
        else:
            workflows = []
        if log_updated:
            messages = get_log_lines(logbuffer, last_logtime,
                                     ['WARNING', 'ERROR'])
        else:
            messages = []
        if workflows or messages:
            return jsonify(workflows=workflows, messages=messages)
        else:
            time.sleep(0.1)
    abort(408)  # Request Timeout


@app.route('/workflow/<workflow:workflow>/download', methods=['GET'],
           defaults={'fname': None})
@app.route('/workflow/<workflow:workflow>/download/<fname>',
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

    # Open ZIP stream
    zstream = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_STORED)
    # Dump configuration to workflow directory
    workflow.config.dump(unicode(workflow.path/'config.yaml'))
    # Find all files within up to two levels deep, relative to the
    # workflow base path
    for fpath in workflow.path.glob('**/*'):
        extract_path = '/'.join((workflow.path.stem,
                                 unicode(fpath.relative_to(workflow.path)))
                                )
        logger.debug("Adding {0} to archive as {1}"
                     .format(fpath, extract_path))
        zstream.write(unicode(fpath), extract_path)
    response = Response(zstream, mimetype='application/zip')
    return response


@app.route('/workflow/<workflow:workflow>/transfer', methods=['POST'])
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
    transfer_to_stick(workflow.id)
    return 'OK'


@app.route('/workflow/<workflow:workflow>/submit', methods=['POST'])
def submit_workflow(workflow):
    """ Submit the requested workflow to the postprocessing server.

    Only available in 'scanner' mode. Requires that the 'postproc_server'
    option is set to the address of a server with the server in 'processor'
    or 'full' mode running.
    """
    if app.config['mode'] not in ('scanner'):
        abort(404)
    server = app.config['postproc_server']
    if not server:
        logger.error("Remote server was not configured, please set the"
                     "'postprocessing_server' value in your configuration!")
        abort(500)
    logger.debug("Creating new workflow on postprocesing server")
    resp = requests.post(server+'/workflow', data=json.dumps(
        {'name': workflow.path.stem,
         'step': 'capture',
         'step_done': True}))
    if not resp:
        logger.error("Error creating remote workflow:\n{0}"
                     .format(resp.content))
        abort(resp.code)
    remote_id = resp.json['id']
    for imgpath in workflow.images:
        logger.debug("Uploading image {0} to postprocessing server"
                     .format(imgpath))
        resp = requests.post("{0}/workflow/{1}/image"
                             .format(server, remote_id),
                             files={'file': {
                                 imgpath.name: imgpath.open('rb').read()}}
                             )
        if not resp:
            logger.error("Error uploading image {0} to postprocessing server:"
                         " \n{1}".format(imgpath, resp.content))
            abort(resp.code)
    resp = requests.post(server+'/queue', data=json.dumps({'id': remote_id}))
    if not resp:
        logger.error("Error putting remote workflow {1} into job queue:: \n{1}"
                     .format(imgpath, resp.content))
        abort(resp.code)
    return ''


# =============== #
#  Queue-related  #
# =============== #
@app.route('/queue', methods=['POST'])
def add_to_queue():
    """ Add a workflow to the processing queue.

    Requires the payload to be a workflow object in JSON notation.
    Returns the queue id.
    """
    data = json.loads(request.data)
    pos = persistence.append_to_queue(data['id'])
    return jsonify({'queue_position': pos})


@app.route('/queue', methods=['GET'])
def list_jobs():
    """ List all items in the processing queue. """
    return json.dumps({jobid: wf
                       for jobid, wf in persistence.get_queue().iteritems()})


@app.route('/queue/<int:pos_idx>', methods=['DELETE'])
def remove_from_queue(pos_idx):
    """ Remove the requested workflow from the processing queue. """
    persistence.delete_from_queue(pos_idx)
    return 'OK'


# =============== #
#  Image-related  #
# =============== #
@app.route('/workflow/<workflow:workflow>/image', methods=['POST'])
def upload_workflow_image(workflow):
    """ Obtain an image for the requested workflow.

    Image must be sent as an attachment with a valid filename and be in either
    JPG or DNG format. Image will be stored in the 'raw' subdirectory of the
    workflow directory.
    """
    allowed = lambda x: x.rsplit('.', 1)[1].lower() in ('jpg', 'jpeg', 'dng')
    file = request.files['file']
    if not allowed(file.filename):
        abort(500, 'Only JPG or DNG files are permitted')
    save_path = workflow.path/'raw'
    if not save_path.exists():
        save_path.mkdir()
    if file and allowed(file.filename):
        filename = secure_filename(file.filename)
        file.save(unicode(save_path/filename))
        return "OK"


@app.route('/workflow/<workflow:workflow>/image/<int:img_num>',
           methods=['GET'])
def get_workflow_image(workflow, img_num):
    """ Return image from requested workflow. """
    # Scale image if requested
    width = request.args.get('width', None)
    try:
        img_path = workflow.images[img_num]
    except IndexError:
        abort(404)
    if width:
        return scale_image(unicode(img_path), width=int(width))
    else:
        return send_file(unicode(img_path))


@app.route('/workflow/<workflow:workflow>/image/<int:img_num>/thumb',
           methods=['GET'])
def get_workflow_image_thumb(workflow, img_num):
    """ Return thumbnail for image from requested workflow. """
    try:
        img_path = workflow.images[img_num]
    except IndexError:
        abort(404)
    cache_key = "{0}.{1}".format(workflow, img_num)
    thumbnail = None
    if not request.args:
        thumbnail = cache.get(cache_key)
    if thumbnail is None:
        thumbnail = get_thumbnail(img_path)
        cache.set(cache_key, thumbnail)
    return Response(thumbnail, mimetype='image/jpeg')


# ================= #
#  Capture-related  #
# ================= #
@app.route('/workflow/<workflow:workflow>/prepare_capture', methods=['POST'])
def prepare_capture(workflow):
    """ Prepare capture for the requested workflow.

    """
    if app.config['mode'] not in ('scanner', 'full'):
        abort(404)
    # Check if any other workflow is active and finish, if neccessary
    logger.debug("Finishing previous workflows")
    for wfid, wf in persistence.get_all_workflows().iteritems():
        if wf.active:
            if wfid == workflow.id:
                return 'OK'
            wf.finish_capture()
    workflow.prepare_capture()
    return 'OK'


@app.route('/workflow/<workflow:workflow>/capture', methods=['POST'])
def trigger_capture(workflow):
    """ Trigger a capture on the requested workflow.

    Optional parameter 'retake' specifies if the last shot is to be retaken.

    Returns the number of pages shot and a list of the images captured by
    this call in JSON notation.
    """
    if app.config['mode'] not in ('scanner', 'full'):
        abort(404)
    if workflow.step != 'capture':
        # TODO: Abort with error, since capture has to be prepared first
        workflow.prepare_capture()
    try:
        workflow.capture(retake=('retake' in request.args))
    except IOError as e:
        logger.error(e)
        abort(500)
    return jsonify({
        'pages_shot': len(workflow.images),
        'images': [get_image_url(workflow, x)
                   for x in workflow.images[-2:]]
    })


@app.route('/workflow/<workflow:workflow>/finish_capture', methods=['POST'])
def finish_capture(workflow):
    """ Wrap up capture process on the requested workflow. """
    if app.config['mode'] not in ('scanner', 'full'):
        abort(404)
    workflow.finish_capture()
    return 'OK'


# ================== #
#   System-related   #
# ================== #
@app.route('/system/shutdown', methods=['POST'])
def shutdown():
    if not app.config['standalone']:
        abort(404)
    # NOTE: This requires that the user running spreads can execute
    #       /sbin/shutdown via sudo.
    logger.info("Shutting device down")
    subprocess.call("/usr/bin/sudo /sbin/shutdown -h now".split())
    return ''

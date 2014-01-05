import json
import logging
import time

import requests
from flask import abort, jsonify, request, send_file, url_for, make_response
from wand.image import Image

import spreads.vendor.confit as confit
from spreads.plugin import (get_pluginmanager, get_relevant_extensions,
                            get_driver)
from spreads.vendor.pathlib import Path
from spreads.workflow import Workflow

import persistence
import util
from spreadsplug.web import app


logger = logging.getLogger('spreadsplub.web')


@app.route('/')
def index():
    return send_file("client/index.html")


# ================== #
#  Workflow-related  #
# ================== #
def _workflow_to_dict(workflow_id, workflow):
    out_dict = dict()
    out_dict['id'] = workflow_id
    out_dict['name'] = workflow.path.name
    out_dict['step'] = workflow.step
    out_dict['step_done'] = workflow.step_done
    out_dict['images'] = [_get_image_url(workflow_id, x)
                          for x in workflow.images] if workflow.images else []
    out_dict['out_files'] = ([unicode(path) for path in workflow.out_files]
                             if workflow.out_files else [])
    out_dict['capture_start'] = workflow.capture_start
    return out_dict

@app.route('/workflow', methods=['POST'])
def create_workflow():
    data = json.loads(request.data)
    path = Path(app.config['base_path'])/data['name']

    # Setup default configuration
    config = confit.Configuration('spreads')
    # Overlay user-supplied values, if existant
    user_config = data.get('config', None)
    if user_config is not None:
        config.set(user_config)
    workflow = Workflow(config=config, path=path,
                        step=data.get('step', None),
                        step_done=data.get('step_done', None))
    workflow_id = persistence.save_workflow(workflow)
    return jsonify(id=workflow_id)


@app.route('/workflow', methods=['GET'])
def list_workflows():
    workflow_list = persistence.get_workflow_list()
    return jsonify(workflows=workflow_list)


@app.route('/workflow/<int:workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    workflow = persistence.get_workflow(workflow_id)
    if workflow is None:
        abort(404)
    return jsonify(_workflow_to_dict(workflow_id, workflow))


@app.route('/workflow/<int:workflow_id>/poll', methods=['GET'])
def poll_for_updates(workflow_id):
    workflow = persistence.get_workflow(workflow_id)
    old_num_caps = len(workflow.images)
    old_step = workflow.step
    old_step_done = workflow.step_done

    while True:
        updated = (len(workflow.images) != old_num_caps
                   or workflow.step != old_step
                   or workflow.step_done != old_step_done)
        if updated:
            return jsonify(_workflow_to_dict(workflow_id, workflow))
        else:
            old_num_caps = len(workflow.images)
            old_step = workflow.step
            old_step_done = workflow.step_done
            time.sleep(0.1)


@app.route('/workflow/<int:workflow_id>/config', methods=['GET'])
def get_workflow_config(workflow_id):
    workflow = persistence.get_workflow(workflow_id)
    if workflow is None:
        abort(404)
    return jsonify(workflow.config.flatten())


@app.route('/workflow/<int:workflow_id>/config', methods=['PUT'])
def update_workflow_config(workflow_id):
    persistence.update_workflow_config(workflow_id, request.data)
    return


@app.route('/workflow/<int:workflow_id>/submit', methods=['POST'])
def submit_workflow(workflow_id):
    if app.config['mode'] not in ('scanner'):
        abort(404)
    workflow = persistence.get_workflow(workflow_id)
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
        resp = requests.post("/".join([server, 'workflow', remote_id,
                                       'image']),
                             files={'file': {imgpath.name: imgpath.read('rb')}}
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
    return


@util.cached
@app.route('/workflow/<int:workflow_id>/options', methods=['GET'])
def get_workflow_config_options(workflow_id):
    workflow = persistence.get_workflow(workflow_id)
    pluginmanager = get_pluginmanager(workflow.config)
    scanner_extensions = ['prepare_capture', 'capture', 'finish_capture']
    processor_extensions = ['process', 'output']
    if app.config['mode'] == 'scanner':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in get_relevant_extensions(
                         pluginmanager, scanner_extensions)}
        templates["device"] = (get_driver(workflow.config["driver"].get())
                               .driver.configuration_template())
    elif app.config['mode'] == 'processor':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in get_relevant_extensions(
                         pluginmanager, processor_extensions)}
    elif app.config['mode'] == 'full':
        templates = {ext.name: ext.plugin.configuration_template()
                     for ext in get_relevant_extensions(
                         pluginmanager,
                         scanner_extensions + processor_extensions)}
        templates["device"] = (get_driver(workflow.config["driver"].get())
                               .driver.configuration_template())
    rv = dict()
    for plugname, options in templates.iteritems():
        if options is None:
            continue
        rv[plugname] = {key: dict(value=option.value,
                                  docstring=option.docstring,
                                  selectable=option.selectable)
                        for key, option in options.iteritems()}
    return jsonify(rv)


# =============== #
#  Queue-related  #
# =============== #
@app.route('/queue', methods=['POST'])
def add_to_queue():
    data = json.loads(request.data)
    pos = persistence.append_to_queue(data['id'])
    return jsonify({'queue_position': pos})


@app.route('/queue', methods=['GET'])
def list_jobs():
    return json.dumps(persistence.get_queue())


@app.route('/queue/<int:queue_pos>', methods=['DELETE'])
def remove_from_queue(pos_idx):
    persistence.delete_from_queue(pos_idx)
    return

# =============== #
#  Image-related  #
# =============== #
def _get_image_url(workflow_id, img_path):
    img_num = int(img_path.stem)
    return url_for('.get_workflow_image',
                   workflow_id=workflow_id,
                   img_num=img_num)


@app.route('/workflow/<int:workflow_id>/image', methods=['POST'])
def upload_workflow_image(workflow_id):
    allowed = lambda x: x.rsplit('.', 1)[1].lower() in ('jpg', 'jpeg', 'dng')
    file = request.files['file']
    if file and allowed(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return "OK"


@app.route('/workflow/<int:workflow_id>/image/<int:img_num>', methods=['GET'])
def get_workflow_image(workflow_id, img_num):
    workflow = persistence.get_workflow(workflow_id)
    try:
        img_path = workflow.images[img_num]
    except IndexError:
        abort(404)
    return send_file(unicode(img_path))


@util.cached
@app.route('/workflow/<int:workflow_id>/image/<int:img_num>/thumb',
           methods=['GET'])
def get_workflow_image_thumb(workflow_id, img_num):
    logger.debug('Generating thumbnail for {0}.{1}'
                 .format(workflow_id, img_num))
    workflow = persistence.get_workflow(workflow_id)
    try:
        img_path = workflow.images[img_num]
    except IndexError:
        abort(404)
    with Image(filename=unicode(img_path)) as img:
        thumb_width = int(300/(img.width/float(img.height)))
        img.sample(300, thumb_width)
        response = make_response(img.make_blob('jpg'))
    response.headers['Content-Type'] = 'image/jpeg'
    return response


# ================= #
#  Capture-related  #
# ================= #
@app.route('/workflow/<int:workflow_id>/capture', methods=['POST'])
def trigger_capture(workflow_id, retake=False):
    if app.config['mode'] not in ('scanner', 'full'):
        abort(404)
    workflow = persistence.get_workflow(workflow_id)
    if workflow.step != 'capture':
        workflow.prepare_capture()
    workflow.capture(retake=retake)
    return jsonify({
        'pages_shot': len(workflow.images),
        'images': [_get_image_url(workflow_id, x)
                   for x in workflow.images[-2:]]
    })


@app.route('/workflow/<int:workflow_id>/capture/finish', methods=['POST'])
def finish_capture(workflow_id):
    if app.config['mode'] not in ('scanner', 'full'):
        abort(404)
    workflow = persistence.get_workflow(workflow_id)
    workflow.finish_capture()
    return 'OK'

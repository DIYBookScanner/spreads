import json
import logging

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
    if app.config['mode'] == 'scanner':
        return send_file("index_scanner.html")


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
    out_dict = dict()
    out_dict['id'] = workflow_id
    out_dict['name'] = workflow.path.name
    out_dict['step'] = workflow.step
    out_dict['step_done'] = workflow.step_done
    out_dict['images'] = [_get_image_url(workflow_id, x)
                          for x in workflow.images]
    out_dict['out_files'] = workflow.out_files
    out_dict['capture_start'] = workflow.capture_start
    return jsonify(out_dict)


@app.route('/workflow/<int:workflow_id>/config', methods=['GET'])
def get_workflow_config(workflow_id):
    workflow = persistence.get_workflow(workflow_id)
    if workflow is None:
        abort(404)
    return jsonify(workflow.config.flatten())


@app.route('/workflow/<int:workflow_id>/config', methods=['PUT'])
def update_workflow_config(workflow_id):
    persistence.update_workflow_config(workflow_id, request.data)


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
    print cache.__dict__
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
    resp = requests.post(server+'/workflow',
                         data=json.dumps({'name': workflow.path.stem}))
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
                             files={'file': {imgpath.stem: imgpath.read('rb')}}
                             )
        if not resp:
            logger.error("Error uploading image {0} to postprocessing server:"
                         " \n{1}".format(imgpath, resp.content))
            abort(resp.code)

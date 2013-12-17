import json
import os

from flask import abort, jsonify, request, send_file

from spreads.workflow import Workflow

from spreadsplug.web import app
import database


@app.route('/')
def index():
    return send_file("index.html")


@app.route('/workflow', methods=['POST'])
def create_workflow():
    data = json.loads(request.data)
    path = os.path.join(app.config['base_path'], data['name'])

    # FIXME: Configuration can't be passed like this
    workflow = Workflow(config=data.get('config', None), path=path,
                        step=data.get('step', None),
                        step_done=data.get('step_done', None))
    workflow_id = database.save_workflow(workflow)
    return jsonify(id=workflow_id)


@app.route('/workflow', methods=['GET'])
def list_workflows():
    workflow_list = database.get_workflow_list()
    return jsonify(workflow_list)


@app.route('/workflow/<int:workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    workflow = database.get_workflow(workflow_id)
    if workflow is None:
        abort(404)
    out_dict = dict()
    out_dict['id'] = workflow_id
    out_dict['name'] = os.path.basename(workflow.path)
    out_dict['step'] = workflow.step
    out_dict['step_done'] = workflow.step_done
    out_dict['images'] = workflow.images
    out_dict['out_files'] = workflow.out_files
    out_dict['capture_start'] = workflow.capture_start
    return jsonify(out_dict)


@app.route('/workflow/<int:workflow_id>/config', methods=['GET'])
def get_workflow_config(workflow_id):
    workflow = database.get_workflow(workflow_id)
    if workflow is None:
        abort(404)
    return jsonify(workflow.config.flatten())


@app.route('/workflow/<int:workflow_id>/config', methods=['PUT'])
def update_workflow_config(workflow_id):
    database.update_workflow_config(workflow_id, request.data)

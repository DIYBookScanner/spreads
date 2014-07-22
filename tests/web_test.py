import json
import os
import random
import re
import time

import jpegtran
import mock
import pytest
from multiprocessing.pool import ThreadPool

from spreads.workflow import signals as workflow_signals
from conftest import TestPluginOutput, TestPluginProcess, TestPluginProcessB


@pytest.yield_fixture
def app(config, tmpdir):
    from spreadsplug.web import WebApplication, app
    from spreadsplug.web.web import event_queue
    config.load_defaults(overwrite=False)

    config['web']['mode'] = 'full'
    config['web']['project_dir'] = unicode(tmpdir.join('workflows'))
    config['web']['debug'] = False
    config['web']['standalone_device'] = True

    webapp = WebApplication(config)
    webapp.setup_logging()
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        webapp.setup_signals()
    webapp.setup_tornado()

    app.config['TESTING'] = True
    event_queue.clear()
    yield app


@pytest.yield_fixture
def client(app):
    yield app.test_client()


@pytest.yield_fixture
def mock_dbus(tmpdir):
    with mock.patch.multiple('dbus', SystemBus=mock.DEFAULT,
                             Interface=mock.DEFAULT) as values:
        stickdir = tmpdir.join('stick')
        stickdir.mkdir()
        mockdevs = [mock.Mock(), mock.Mock()]*2
        mockobj = mock.MagicMock()
        mockobj.get_dbus_method.return_value.return_value = unicode(
            stickdir)
        mockobj.EnumerateDevices.return_value = mockdevs
        mockobj.Get.side_effect = [True, 'usb', True]*2
        values['Interface'].return_value = mockobj
        yield mockobj


@pytest.yield_fixture
def worker():
    from spreadsplug.web.worker import ProcessingWorker
    worker = ProcessingWorker()
    worker.start()
    time.sleep(0.1)
    yield
    worker.stop()


def create_workflow(client, num_captures='random'):
    workflow = {
        'metadata': {'title': 'test{0}'.format(random.randint(0, 8192))},
    }
    data = json.loads(client.post('/api/workflow',
                      data=json.dumps(workflow)).data)
    if num_captures:
        client.post('/api/workflow/{0}/prepare_capture'.format(data['id']))
        for _ in xrange(random.randint(1, 4)
                        if num_captures == 'random' else num_captures):
            client.post('/api/workflow/{0}/capture'.format(data['id']))
        client.post('/api/workflow/{0}/finish_capture'.format(data['id']))
    return data['id']


def test_index(client):
    rv = client.get('/')
    assert "<title>spreads</title>" in rv.data
    assert "<script src=\"/static/bundle.js\"></script>" in rv.data

    cfg = json.loads(re.findall(r"window.config = ({.*});", rv.data)[0])
    assert cfg['plugins'] == ['test_output', 'test_process', 'test_process2']
    assert cfg['driver'] == 'testdriver'
    assert cfg['web']['mode'] == 'full'
    templates = json.loads(re.findall(r"window.pluginTemplates = ({.*});",
                                      rv.data)[0])
    assert 'a_boolean' in templates['test_process']
    assert 'flip_target_pages' in templates['device']
    assert 'string' in templates['test_output']


def test_get_plugins(client):
    exts = [mock.Mock(), mock.Mock(), mock.Mock()]
    exts[0].name = "test_output"
    exts[0].load.return_value = TestPluginOutput
    exts[1].name = "test_process"
    exts[1].load.return_value = TestPluginProcess
    exts[2].name = "test_process2"
    exts[2].load.return_value = TestPluginProcessB
    with mock.patch('spreadsplug.web.web.pkg_resources') as pkgr:
        pkgr.iter_entry_points.return_value = exts
        rv = client.get('/api/plugins')
    plugins = json.loads(rv.data)
    assert plugins['output'] == ["test_output"]
    assert plugins['postprocessing'] == ["test_process", "test_process2"]


def test_get_plugin_templates(client):
    rv = client.get('/api/plugins/templates')
    templates = json.loads(rv.data)
    assert 'a_boolean' in templates['test_process']
    assert 'flip_target_pages' in templates['device']
    assert 'string' in templates['test_output']


def test_create_workflow(client):
    wf = json.dumps({
        'metadata': {'title': 'A Test Workflow'}
    })
    data = json.loads(client.post('/api/workflow', data=wf).data)
    workflow_id = data['id']
    data = json.loads(client.get('/api/workflow/{0}'.format(workflow_id)).data)
    assert data['metadata'] == {'title': 'A Test Workflow'}
    assert data['slug'] == 'a-test-workflow'


def test_list_workflows(client):
    for _ in xrange(5):
        create_workflow(client)
    data = json.loads(client.get('/api/workflow').data)
    assert isinstance(data, list)
    assert len(data) == 5
    assert 'config' in data[0]


def test_get_workflow(client):
    wfid = create_workflow(client)
    data = json.loads(client.get('/api/workflow/{0}'.format(wfid)).data)
    assert 'test_output' in data['config']['plugins']


def test_update_workflow(client):
    wfid = create_workflow(client)
    workflow = json.loads(client.get('/api/workflow/{0}'.format(wfid)).data)
    workflow['config']['device']['flip_target_pages'] = True
    data = json.loads(
        client.put('/api/workflow/{0}'.format(wfid), data=json.dumps(workflow))
        .data)
    assert data['config']['device']['flip_target_pages']


def test_delete_workflow(client):
    wfid = create_workflow(client)
    client.delete('/api/workflow/{0}'.format(wfid))
    data = json.loads(client.get('/api/workflow').data)
    assert len(data) == 0


def test_poll(client):
    pool = ThreadPool(processes=1)
    asyn_result = pool.apply_async(client.get, ('/api/poll', ))
    time.sleep(.1)
    workflow_signals['workflow:removed'].send(None, id=1)
    rv = asyn_result.get()
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data == [{'name': 'workflow:removed',
                     'data': {'id': 1}}]


def test_transfer_workflow(client, mock_dbus, tmpdir):
    wfid = create_workflow(client, 10)
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        client.post('/api/workflow/{0}/transfer'.format(wfid))
    assert len([x for x in tmpdir.visit('stick/*/data/raw/*.jpg')]) == 20


@mock.patch('spreadsplug.web.tasks.requests')
def test_submit_workflow(requests, app, tmpdir):
    app.config['postproc_server'] = 'http://127.0.0.1:5000'
    app.config['mode'] = 'scanner'
    client = app.test_client()
    wfid = create_workflow(client)
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        requests.post.return_value.json.return_value = {'id': 1}
        client.post('/api/workflow/{0}/submit'.format(wfid),
                    content_type="application/json",
                    data=json.dumps({'config': {'plugins': []},
                                     'server': '127.0.0.1:5000'}))
    assert requests.post.call_count == 1
    # TODO: Iterate through data, assert events are emitted
    # TODO: Assert completed are emitted


def test_get_page_image(client):
    wfid = create_workflow(client)
    with open(os.path.abspath('./tests/data/even.jpg'), 'rb') as fp:
        orig = fp.read()
    fromapi = client.get('/api/workflow/{0}/page/0/raw'.format(wfid)).data
    assert orig == fromapi


def test_get_page_image_scaled(client):
    wfid = create_workflow(client)
    rv = client.get('/api/workflow/{0}/page/0/raw?width=300'.format(wfid))
    assert rv.status_code == 200
    img = jpegtran.JPEGImage(blob=rv.data)
    assert img.width == 300


def test_get_page_image_thumb(client):
    # TODO: Use test images that actually have an EXIF thumbnail...
    wfid = create_workflow(client)
    rv = client.get('/api/workflow/{0}/page/1/raw/thumb'.format(wfid))
    assert rv.status_code == 200
    assert jpegtran.JPEGImage(blob=rv.data).width == 196


def test_prepare_capture(client):
    wfid = create_workflow(client, num_captures=None)
    rv = client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
    assert rv.status_code == 200
    client.post('/api/workflow/{0}/finish_capture'.format(wfid))
    # TODO: Verify workflow was prepared, verify right data
    #       was returned


def test_prepare_capture_when_other_active(client):
    wfid = create_workflow(client, num_captures=None)
    client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
    client.post('/api/workflow/{0}/capture'.format(wfid))
    wfid = create_workflow(client, num_captures=None)
    assert (client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
            .status_code) == 200
    client.post('/api/workflow/{0}/finish_capture'.format(wfid))


def test_capture(client):
    wfid = create_workflow(client, num_captures=None)
    assert (client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
            .status_code) == 200
    assert (client.post('/api/workflow/{0}/capture'.format(wfid))
            .status_code) == 200
    client.post('/api/workflow/{0}/finish_capture'.format(wfid))
    # TODO: Verify it was triggered on the workflow, verify
    #       the right data was returned


def test_finish_capture(client):
    wfid = create_workflow(client, num_captures=None)
    assert (client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
            .status_code) == 200
    assert (client.post('/api/workflow/{0}/capture'.format(wfid))
            .status_code) == 200
    assert (client.post('/api/workflow/{0}/finish_capture'.format(wfid))
            .status_code) == 200


def test_shutdown(client):
    with mock.patch('spreadsplug.web.web.subprocess.call') as sp:
        client.post('/api/system/shutdown')
    sp.assert_called_once_with(['/usr/bin/sudo',
                                '/sbin/shutdown', '-h', 'now'])


def test_start_processing(client):
    wfid = create_workflow(client, num_captures=None)
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        client.post('/api/workflow/{0}/process'.format(wfid))
    time.sleep(.1)
    update_events = [e['data']['changes']['status']
                     for e in json.loads(client.get('/api/events').data)
                     if (e['name'] == 'workflow:modified'
                         and 'status' in e['data']['changes'])]
    assert len(update_events) == 4
    assert all(e['step'] == 'process' for e in update_events)
    assert update_events[0]['step_progress'] is None
    assert update_events[1]['step_progress'] == 0
    assert update_events[2]['step_progress'] == 0.5
    assert update_events[3]['step_progress'] == 1.0
    # TODO: Verify generation was completed (files?)


def test_start_outputting(client):
    wfid = create_workflow(client, num_captures=None)
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        client.post('/api/workflow/{0}/output'.format(wfid))
    time.sleep(.1)
    update_events = [e['data']['changes']['status']
                     for e in json.loads(client.get('/api/events').data)
                     if (e['name'] == 'workflow:modified'
                         and 'status' in e['data']['changes'])]
    assert len(update_events) == 3
    assert all(e['step'] == 'output' for e in update_events)
    assert update_events[0]['step_progress'] is None
    assert update_events[1]['step_progress'] == 0
    assert update_events[2]['step_progress'] == 1.0
    # TODO: Verify generation was completed (files?)


def test_get_logs(client):
    create_workflow(client, num_captures=1)
    records = json.loads(client.get('/api/log',
                                    query_string={'start': 2, 'count': 5,
                                                  'level': 'debug'}).data)
    assert len(records['messages']) == 5
    assert (records['messages'][0]['message']
            == u'Sending finish_capture command to devices')

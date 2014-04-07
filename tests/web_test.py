import json
import os
import random
import re
import StringIO
import time
import zipfile

import jpegtran
import mock
import pytest
from multiprocessing.pool import ThreadPool

from spreads.workflow import Workflow


@pytest.yield_fixture
def app(config, tmpdir):
    import spreadsplug.web.persistence as persistence
    from spreadsplug.web import setup_app, setup_logging, setup_signals, app
    from spreadsplug.web.web import event_queue
    config.load_defaults(overwrite=False)

    config['web']['mode'] = 'full'
    config['web']['database'] = unicode(tmpdir.join('test.db'))
    config['web']['project_dir'] = unicode(tmpdir)
    config['web']['debug'] = False
    config['web']['standalone_device'] = True
    setup_app(config)
    setup_logging(config)
    setup_signals()
    app.config['TESTING'] = True
    event_queue.clear()
    persistence.WorkflowCache = {}
    yield app


@pytest.yield_fixture
def client(app):
    yield app.test_client()


@pytest.yield_fixture
def mock_dbus(tmpdir):
    try:
        with mock.patch.multiple('dbus', SystemBus=mock.DEFAULT,
                                 Interface=mock.DEFAULT) as values:
            stickdir = tmpdir.join('stick')
            stickdir.mkdir()
            mockdevs = [mock.Mock(), mock.Mock()]*2
            mockobj = mock.MagicMock()
            mockobj.get_dbus_method.return_value.return_value = unicode(stickdir)
            mockobj.EnumerateDevices.return_value = mockdevs
            mockobj.Get.side_effect = [True, 'usb', True]*2
            values['Interface'].return_value = mockobj
            yield mockobj
    except ImportError:
        with mock.patch('spreadsplug.web.util.subprocess') as sp:
            sp.check_output.side_effect = ("""
node /org/freedesktop/UDisks/devices {
  node /org/freedesktop/UDisks/devices/sda {
    interface org.freedesktop.UDisks.Device {
      properties:
        readonly s SomeVal = '';
        readonly t DriveConnectionInterface = 'ata';
        readonly b DeviceIsPartition = false;
        readonly s DeviceFile = '/dev/sda';
    };
  };
  node /org/freedesktop/UDisks/devices/sdc1 {
    interface org.freedesktop.UDisks.Device {
      properties:
        readonly s SomeVal = '';
        readonly t DriveConnectionInterface = 'usb';
        readonly b DeviceIsPartition = true;
        readonly s DeviceFile = '/dev/sdc1';
    };
  };
};
            """, tmpdir.join('stick'), True)
            yield sp


@pytest.fixture
def jsonworkflow():
    return json.dumps({
        'name': 'foobar'
    })


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
        'name': 'test{0}'.format(random.randint(0, 8192)),
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
    assert "<script src=\"/static/spreads.min.js\"></script>" in rv.data

    cfg = json.loads(re.findall(r"window.config = ({.*});", rv.data)[0])
    assert cfg['plugins'] == ['test_output', 'test_process', 'test_process2']
    assert cfg['driver'] == 'testdriver'
    assert cfg['web']['mode'] == 'full'
    templates = json.loads(re.findall(r"window.pluginTemplates = ({.*});",
                                      rv.data)[0])
    assert 'a_boolean' in templates['test_process']
    assert 'flip_target_pages' in templates['device']
    assert 'string' in templates['test_output']


def test_create_workflow(client, jsonworkflow):
    data = json.loads(client.post('/api/workflow', data=jsonworkflow).data)
    workflow_id = data['id']
    data = json.loads(client.get('/api/workflow/{0}'.format(workflow_id)).data)
    assert data['name'] == 'foobar'
    assert data['id'] == 1


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
    assert data['step'] == 'capture'


def test_update_workflow(client):
    wfid = create_workflow(client)
    workflow = json.loads(client.get('/api/workflow/{0}'.format(wfid)).data)
    workflow['config']['foo'] = 'bar'
    data = json.loads(
        client.put('/api/workflow/{0}'.format(wfid), data=json.dumps(workflow))
        .data)
    assert data['config']['foo'] == 'bar'


def test_delete_workflow(client):
    wfid = create_workflow(client)
    client.delete('/api/workflow/{0}'.format(wfid))
    data = json.loads(client.get('/api/workflow').data)
    assert len(data) == 0


def test_poll(client):
    pool = ThreadPool(processes=1)
    asyn_result = pool.apply_async(client.get, ('/api/poll', ))
    time.sleep(.1)
    Workflow.on_removed.send(None, id=1)
    rv = asyn_result.get()
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data == [{'name': 'workflow:removed',
                     'data': {'id': 1}}]


def test_download_workflow(client):
    wfid = create_workflow(client, 10)
    resp = client.get('/api/workflow/{0}/download'.format(wfid),
                      follow_redirects=True)
    zfile = zipfile.ZipFile(StringIO.StringIO(resp.data))
    assert len([x for x in zfile.namelist()
                if '/raw/' in x and x.endswith('jpg')]) == 20


def test_transfer_workflow(client, mock_dbus, tmpdir):
    wfid = create_workflow(client, 10)
    with mock.patch('spreadsplug.web.task_queue') as mock_tq:
        mock_tq.task.return_value = lambda x: x
        client.post('/api/workflow/{0}/transfer'.format(wfid))
    assert len([x for x in tmpdir.visit('stick/*/raw/*.jpg')]) == 20


def test_submit_workflow(app, tmpdir):
    app.config['postproc_server'] = 'http://127.0.0.1:5000'
    app.config['mode'] = 'scanner'
    client = app.test_client()
    wfid = create_workflow(client)
    with mock.patch('spreadsplug.web.web.requests.post') as post:
        post.return_value.json = {'id': 1}
        client.post('/api/workflow/{0}/submit'.format(wfid))
    wfname = json.loads(client.get('/api/workflow/{0}'.format(wfid)).data)['name']
    for img in tmpdir.join(wfname, 'raw').listdir():
        post.assert_any_call('http://127.0.0.1:5000/api/workflow/{0}/image'
                             .format(wfid),
                             files={'file': {
                                 img.basename: img.open('rb').read()}})


def test_upload_workflow_image(client, tmpdir):
    wfid = create_workflow(client, num_captures=None)
    client.post('/api/workflow/{0}/image'.format(wfid),
                data={'file': ('./tests/data/even.jpg', '000.jpg')})
    wfdata = json.loads(client.get('/api/workflow/{0}'.format(wfid)).data)
    assert len(wfdata['images']) == 1
    assert tmpdir.join(wfdata['name'], 'raw', '000.jpg').exists()
    resp = client.post('/api/workflow/{0}/image'.format(wfid),
                       data={'file': ('./tests/data/even.jpg', '000.png')})
    assert resp.status_code == 500


def test_get_workflow_image(client):
    wfid = create_workflow(client)
    with open(os.path.abspath('./tests/data/even.jpg'), 'rb') as fp:
        orig = fp.read()
    fromapi = client.get('/api/workflow/{0}/image/0'.format(wfid)).data
    assert orig == fromapi


def test_get_workflow_image_scaled(client):
    wfid = create_workflow(client)
    img = jpegtran.JPEGImage(blob=client.get(
        '/api/workflow/{0}/image/0?width=300'.format(wfid)).data)
    assert img.width == 300


def test_get_workflow_image_thumb(client):
    # TODO: Use test images that actually have an EXIF thumbnail...
    wfid = create_workflow(client)
    rv = client.get('/api/workflow/{0}/image/1/thumb'.format(wfid))
    assert rv.status_code == 200
    assert jpegtran.JPEGImage(blob=rv.data).width


def test_prepare_capture(client):
    wfid = create_workflow(client, num_captures=None)
    rv = client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
    assert rv.status_code == 200
    # TODO: Verify workflow was prepared, verify right data
    #       was returned


def test_prepare_capture_when_other_active(client):
    wfid = create_workflow(client, num_captures=None)
    client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
    client.post('/api/workflow/{0}/capture'.format(wfid))
    wfid = create_workflow(client, num_captures=None)
    assert (client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
            .status_code) == 200


def test_capture(client):
    wfid = create_workflow(client, num_captures=None)
    assert (client.post('/api/workflow/{0}/prepare_capture'.format(wfid))
            .status_code) == 200
    assert (client.post('/api/workflow/{0}/capture'.format(wfid))
            .status_code) == 200
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


def test_get_logs(client):
    create_workflow(client, num_captures=1)
    records = json.loads(client.get('/api/log',
                                    query_string={'start': 2, 'count': 5,
                                                  'level': 'debug'}).data)
    assert len(records['messages']) == 5
    assert (records['messages'][0]['message']
            == u'Sending finish_capture command to devices')

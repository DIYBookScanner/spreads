import json
import os
import shutil
import unittest

import spreadsplug.web as web


class TestWebScanner(unittest.TestCase):
    def setUp(self):
        print "Setting up webtest"
        web.app.config['TESTING'] = True
        web.app.config['mode'] = 'scanner'
        web.app.config['database'] = 'test/test.db'
        print "Creating dir"
        os.mkdir('/tmp/spreadstest')
        web.app.config['base_path'] = '/tmp/spreadstest'
        self.app = web.app.test_client()

    def tearDown(self):
        shutil.rmtree(web.app.config['base_path'])

    def test_get_index(self):
        rv = self.app.get('/')
        assert "<title>spreads-scanner</title>" in rv.data

    def test_create_workflow(self):
        web.app.config['database'] = '/tmp/spreadstest.db'
        data = {'name': 'foo', 'step': 'process'}
        rv = self.app.post('/workflow', data=json.dumps(data))
        data = json.loads(rv.data)
        workflow_id = data['id']
        rv = self.app.get('/workflow/{0}'.format(workflow_id))
        data = json.loads(rv.data)
        os.remove('/tmp/spreadstest.db')
        assert data['name'] == 'foo'
        assert data['step'] == 'process'

    def test_list_workflows(self):
        rv = self.app.get('/workflow')
        data = json.loads(rv.data)
        assert len(data['workflows']) == 2
        assert data['workflows'][0]['name'] == 'foo'
        assert data['workflows'][0]['step'] == 'capture'
        assert data['workflows'][1]['name'] == 'bar'

    def test_get_workflow(self):
        rv = self.app.get('/workflow/1')
        data = json.loads(rv.data)
        assert data['name'] == 'foo'
        assert data['capture_start'] == 1387408206

    def test_get_workflow_config(self):
        rv = self.app.get('/workflow/1/config')
        data = json.loads(rv.data)
        assert data['device']['sensitivity'] == 80

    def test_get_workflow_config_options(self):
        rv = self.app.get('/workflow/1/options')
        data = json.loads(rv.data)
        assert data['device'] == {}
        web.app.config['mode'] = 'full'
        rv = self.app.get('/workflow/2/options')
        data = json.loads(rv.data)
        assert (data['scantailor']['auto_margins'] ==
                {'docstring': 'Automatically detect margins',
                 'selectable': False,
                 'value': True})

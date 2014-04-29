from __future__ import division, unicode_literals

import shutil

import pytest

import spreads.util as util
import spreads.workflow
from conftest import TestDriver


@pytest.fixture
def workflow(config, tmpdir):
    # NOTE: To avoid accessing the filesystem and to have more control, we
    #       monkey-patch the relevant methods to be mocks.
    return spreads.workflow.Workflow(config=config, path=unicode(tmpdir))


def test_get_plugins(workflow):
    plugins = workflow.plugins
    names = [x.__name__ for x in plugins]
    assert 'test_output' in names
    assert 'test_process' in names
    assert 'test_process2' in names


def test_get_devices(workflow):
    devices = workflow.devices
    assert len(devices) == 2
    # TODO: Verify


def test_get_devices_no_device(workflow):
    TestDriver.num_devices = 0
    with pytest.raises(util.DeviceException):
        _ = workflow.devices
    TestDriver.num_devices = 2


def test_get_next_filename(workflow):
    root_path = workflow.path/'data'/'raw'
    fname = workflow._get_next_filename(target_page='odd')
    assert unicode(fname) == unicode(root_path/"001")
    fname = workflow._get_next_filename(target_page='even')
    assert unicode(fname) == unicode(root_path/"000")

    shutil.copyfile('./tests/data/even.jpg', unicode(root_path/'000.jpg'))
    shutil.copyfile('./tests/data/odd.jpg', unicode(root_path/'001.jpg'))

    fname = workflow._get_next_filename(target_page='odd')
    assert unicode(fname) == unicode(root_path/"003")
    fname = workflow._get_next_filename(target_page='even')
    assert unicode(fname) == unicode(root_path/"002")


def test_prepare_capture(workflow):
    workflow.prepare_capture()
    assert workflow.prepared
    assert workflow.active
    assert workflow.step == 'capture'
    workflow.finish_capture()


def test_capture(workflow):
    workflow.config['device']['parallel_capture'] = True
    workflow.config['device']['flip_target_pages'] = False
    for dev in workflow.devices:
        dev.delay = 0.25
    workflow.prepare_capture()
    workflow.capture()
    assert workflow.pages_shot == 2
    assert (workflow.images[1].stat().st_ctime -
            workflow.images[0].stat().st_ctime) < 0.25
    workflow.finish_capture()


def test_capture_noparallel(workflow):
    workflow.config['device']['parallel_capture'] = False
    workflow.config['device']['flip_target_pages'] = False
    for dev in workflow.devices:
        dev.delay = 0.25
    workflow.prepare_capture()
    workflow.capture()
    assert workflow.pages_shot == 2
    assert round(workflow.images[1].stat().st_ctime -
                 workflow.images[0].stat().st_ctime, 2) >= 0.25
    workflow.finish_capture()


def test_capture_flip_target_pages(workflow):
    workflow.config['device']['parallel_capture'] = False
    workflow.config['device']['flip_target_pages'] = True
    workflow.prepare_capture()
    workflow.capture()
    # TODO: Verify
    workflow.finish_capture()


def test_finish_capture(workflow):
    workflow.prepare_capture()
    workflow.finish_capture()
    # TODO: Verify


def test_process(workflow):
    workflow.process()
    # TODO: Verify


def test_output(workflow):
    workflow.output()
    # TODO: Verify

from __future__ import division, unicode_literals

import pytest
from mock import Mock

import spreads.util as util
import spreads.workflow
from conftest import TestDriver


@pytest.fixture
def workflow(config, tmpdir):
    return spreads.workflow.Workflow(config=config, path=unicode(tmpdir))


def test_get_plugins(workflow):
    plugins = workflow._plugins
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
        _ = workflow.devices  # noqa
    TestDriver.num_devices = 2


def test_get_next_capture_page(workflow):
    root_path = workflow.path/'data'/'raw'
    page = workflow._get_next_capture_page(target_page='odd')
    assert unicode(page.raw_image) == unicode(root_path/"001.jpg")
    page = workflow._get_next_capture_page(target_page='even')
    assert unicode(page.raw_image) == unicode(root_path/"000.jpg")

    workflow.pages.append(Mock(capture_num=0))
    workflow.pages.append(Mock(capture_num=1))

    page = workflow._get_next_capture_page(target_page='odd')
    assert unicode(page.raw_image) == unicode(root_path/"003.jpg")
    page = workflow._get_next_capture_page(target_page='even')
    assert unicode(page.raw_image) == unicode(root_path/"002.jpg")

    workflow.pages.append(Mock(capture_num=2))
    workflow.pages.append(Mock(capture_num=3))

    workflow.config['device']['shoot_raw'] = True
    page = workflow._get_next_capture_page(target_page='even')
    assert unicode(page.raw_image) == unicode(root_path/"004.dng")


def test_prepare_capture(workflow):
    workflow.prepare_capture()
    assert workflow.status['prepared']
    assert workflow.status['step'] == 'capture'
    workflow.finish_capture()


def test_capture(workflow):
    workflow.config['device']['parallel_capture'] = True
    workflow.config['device']['flip_target_pages'] = False
    for dev in workflow.devices:
        dev.delay = 1.0  # subsecond checks fails on some filesystems
    workflow.prepare_capture()
    workflow.capture()
    assert len(workflow.pages) == 2
    assert (workflow.pages[1].raw_image.stat().st_ctime -
            workflow.pages[0].raw_image.stat().st_ctime) < 1.0
    workflow.finish_capture()


def test_capture_noparallel(workflow):
    workflow.config['device']['parallel_capture'] = False
    workflow.config['device']['flip_target_pages'] = False
    for dev in workflow.devices:
        dev.delay = 1.0  # subsecond checks fails on some filesystems
    workflow.prepare_capture()
    workflow.capture()
    assert len(workflow.pages) == 2
    assert round(workflow.pages[1].raw_image.stat().st_ctime -
                 workflow.pages[0].raw_image.stat().st_ctime, 2) >= 1.0
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

# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

import copy
import logging
import shutil

import blinker
import requests
from spreads.vendor.pathlib import Path

from spreadsplug.web import task_queue
from persistence import get_workflow
from util import find_stick

logger = logging.getLogger('spreadsplug.web.tasks')
signals = blinker.Namespace()
on_transfer_started = signals.signal('transfer:started')
on_transfer_progressed = signals.signal('transfer:progressed')
on_transfer_completed = signals.signal('transfer:completed')
on_submit_started = signals.signal('submit:started')
on_submit_progressed = signals.signal('submit:progressed')
on_submit_completed = signals.signal('submit:completed')


@task_queue.task()
def transfer_to_stick(workflow_id):
    stick = find_stick()
    workflow = get_workflow(workflow_id)
    files = list(workflow.path.rglob('*'))
    num_files = len(files)
    # Filter out problematic characters
    clean_name = (workflow.path.name.replace(':', '_')
                                    .replace('/', '_'))
    workflow.step = 'transfer'
    workflow.step_done = False
    try:
        mount = stick.get_dbus_method(
            "FilesystemMount", dbus_interface="org.freedesktop.UDisks.Device")
        mount_point = mount('', [])
        target_path = Path(mount_point)/clean_name
        if target_path.exists():
            shutil.rmtree(unicode(target_path))
        target_path.mkdir()
        signals['transfer:started'].send(workflow)
        for num, path in enumerate(files, 1):
            signals['transfer:progressed'].send(
                workflow, progress=(num/num_files)*0.79, status=path.name)
            target = target_path/path.relative_to(workflow.path)
            if path.is_dir():
                target.mkdir()
            else:
                shutil.copyfile(unicode(path), unicode(target))
    finally:
        if 'mount_point' in locals():
            signals['transfer:progressed'].send(workflow, progress=0.8,
                                                status="Syncing...")
            unmount = stick.get_dbus_method(
                "FilesystemUnmount",
                dbus_interface="org.freedesktop.UDisks.Device")
            unmount([], timeout=1e6)  # dbus-python doesn't know an infinite
                                      # timeout... unmounting sometimes takes a
                                      # long time, since the device has to be
                                      # synced.
        workflow.step_done = True
        signals['transfer:completed'].send(workflow)


@task_queue.task()
def upload_workflow(workflow_id, endpoint):
    # TODO: Obtain config and dump into data/config.yaml inside of zstream
    logger.debug("Uploading workflow to postprocessing server")
    workflow = get_workflow(workflow_id)
    zstream = workflow.bag.package_as_zipstream(compression=None)
    zstream_copy = copy.deepcopy(zstream)
    num_data = sum(1 for x in zstream_copy)

    def zstream_wrapper():
        """ Wrapper around our zstream so we can emit a signal when all data
        has been streamed to the client.
        """
        for num, data in enumerate(zstream):
            signals['submit:progressed'].send(
                workflow, progress=(num/num_data),
                status="Uploading workflow...")
            yield data

    signals['submit:started'].send(workflow)
    resp = requests.post(endpoint, data=zstream_wrapper(),
                         headers={'Content-Type': 'application/zip'})
    if not resp:
        signals['submit:completed'].send(workflow, error=resp.content)
        logger.error("Upload failed: {0}".format(resp.content))
    else:
        signals['submit:completed'].send(workflow, remote_id=resp.json()['id'])


@task_queue.task()
def process_workflow(workflow_id):
    workflow = get_workflow(workflow_id)
    workflow.process()


@task_queue.task()
def output_workflow(workflow_id):
    workflow = get_workflow(workflow_id)
    workflow.output()

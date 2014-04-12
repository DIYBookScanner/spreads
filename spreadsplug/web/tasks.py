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

import logging
import shutil

from spreads.vendor.pathlib import Path

from spreadsplug.web import task_queue
from persistence import get_workflow
from util import find_stick
from web import (on_transfer_started, on_transfer_progressed,
                 on_transfer_completed)

logger = logging.getLogger('spreadsplug.web.tasks')


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
        on_transfer_started.send(workflow)
        for num, path in enumerate(files, 1):
            on_transfer_progressed.send(workflow,
                                        progress=(num/num_files)*0.79,
                                        status=path.name)
            target = target_path/path.relative_to(workflow.path)
            if path.is_dir():
                target.mkdir()
            else:
                shutil.copyfile(unicode(path), unicode(target))
    finally:
        if 'mount_point' in locals():
            on_transfer_progressed.send(workflow, progress=0.8,
                                        status="Syncing...")
            unmount = stick.get_dbus_method(
                "FilesystemUnmount",
                dbus_interface="org.freedesktop.UDisks.Device")
            unmount([], timeout=1e6)  # dbus-python doesn't know an infinite
                                      # timeout... unmounting sometimes takes a
                                      # long time, since the device has to be
                                      # synced.
        workflow.step_done = True
        on_transfer_completed.send(workflow)

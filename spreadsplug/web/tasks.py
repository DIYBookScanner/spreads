import json
import logging
import shutil

import requests
from spreads.vendor.pathlib import Path

from spreadsplug.web import task_queue
from util import find_stick, mount_stick
from persistence import get_workflow, save_workflow

logger = logging.getLogger('spreadsplug.web.tasks')


@task_queue.task()
def transfer_to_stick(workflow_id):
    stick = find_stick()
    workflow = get_workflow(workflow_id)
    with mount_stick(stick) as p:
        workflow.step = 'transfer'
        workflow.step_done = False
        # Filter out problematic characters
        clean_name = (workflow.path.name.replace(':', '_')
                                        .replace('/', '_'))
        target_path = Path(p)/clean_name
        if target_path.exists():
            shutil.rmtree(unicode(target_path))
        try:
            shutil.copytree(unicode(workflow.path), unicode(target_path))
        except shutil.Error as e:
            # Error 38 means that some permissions could not be copied, this is
            # expected behaviour for filesystems like FAT32 or exFAT, so we
            # silently ignore it here, since the actual data will have been
            # copied nevertheless.
            if any("[Errno 38]" not in exc for src, dst, exc in e[0]):
                raise e
        workflow.step_done = True

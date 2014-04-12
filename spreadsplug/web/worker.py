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

import logging
import threading
import time

from persistence import pop_from_queue


class ProcessingWorker(object):
    current_workflow = None
    current_step = None

    _exit_event = threading.Event()
    _worker_thread = None

    def __init__(self):
        self.logger = logging.getLogger('spreadsplug.web.worker')

    def start(self):
        self.logger.debug("Starting worker thread")
        self._worker_thread = threading.Thread(target=self._run)
        self._worker_thread.start()

    def stop(self):
        self.logger.debug("Stopping worker thread")
        self._exit_event.set()

    def _run(self):
        self.logger.debug("Worker thread commencing.")
        while not self._exit_event.is_set():
            workflow = pop_from_queue()
            if workflow is not None:
                self.logger.info("Starting processing of workflow '{0}'"
                                 .format(workflow.path.stem))
                workflow.process()
                self.logger.info("Starting output generation of workflow '{0}'"
                                 .format(workflow.path.stem))
                workflow.output()
            time.sleep(1)
        self.logger.debug("Thread has finished")

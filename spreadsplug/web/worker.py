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
            time.sleep(5)
        self.logger.debug("Thread has finished")

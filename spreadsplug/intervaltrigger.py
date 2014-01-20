import logging
import threading
import time

from spreads.plugin import HookPlugin, PluginOption

logger = logging.getLogger('spreadsplug.intervaltrigger')


class IntervalTrigger(HookPlugin):
    __name__ = 'intervaltrigger'

    _loop_thread = None
    _exit_event = None

    @classmethod
    def configuration_template(cls):
        return {'interval': PluginOption(5, "Interval between captures"
                                            " (in seconds)")}

    def start_trigger_loop(self, capture_callback):
        logger.debug("Starting event loop")
        self._exit_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._trigger_loop,
                                             args=(capture_callback, ))
        self._loop_thread.start()

    def stop_trigger_loop(self):
        logger.debug("Stopping event loop")
        self._exit_event.set()

    def _trigger_loop(self, capture_func):
        interval = self.config['interval'].get(int)
        while True:
            sleep_time = 0
            while sleep_time < interval:
                if self._exit_event.is_set():
                    return
                time.sleep(0.01)
                sleep_time += 0.01
            capture_func()

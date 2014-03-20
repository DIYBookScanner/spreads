import hidapi
import logging
import threading
import time

from spreads.plugin import HookPlugin, TriggerHooksMixin
from spreads.util import DeviceException


class HidTrigger(HookPlugin, TriggerHooksMixin):
    __name__ = 'hidtrigger'

    _loop_thread = None
    _exit_event = None

    def __init__(self, config):
        self._logger = logging.getLogger('spreadsplug.hidtrigger')
        self._logger.debug("Initializing HidTrigger plugin")

    def start_trigger_loop(self, capture_callback):
        self._hid_devs = []
        for dev in self._find_devices():
            self._logger.debug("Found HID device: {0}".format(dev))
            self._hid_devs.append(dev)
        if not self._hid_devs:
            self._logger.warning("Could not find any HID devices.")
            return
        self._exit_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._trigger_loop,
                                             args=(capture_callback, ))
        self._logger.debug("Starting trigger loop")
        self._loop_thread.start()

    def stop_trigger_loop(self):
        if self._exit_event is None:
            # Return if no loop thread is running
            return
        self._logger.debug("Stopping trigger loop")
        self._exit_event.set()
        self._loop_thread.join()

    def _trigger_loop(self, capture_func):
        # Polls all attached HID devices for a press->release event and
        # trigger a capture.
        while not self._exit_event.is_set():
            for dev in self._hid_devs:
                # See if there's input
                if dev.read(8):
                    # Wait for key release
                    while not dev.read(8):
                        time.sleep(0.01)
                        continue
                    capture_func()
                else:
                    time.sleep(0.01)

    def _find_devices(self):
        for candidate in hidapi.enumerate():
            try:
                dev = hidapi.Device(candidate, blocking=False)
            except IOError:
                raise DeviceException("Could not open HID device, please check"
                                      " your permissions on /dev/bus/usb.")
            yield dev

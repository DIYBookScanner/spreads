import hid
import threading
import time

from spreads.plugin import HookPlugin
from spreads.util import DeviceException


class HidTrigger(HookPlugin):
    _loop_thread = None
    _exit_event = None

    def start_trigger_loop(self, capture_callback):
        self._hid_devs = []
        for dev in self._find_devices():
            dev.set_nonblocking(True)
            # Set device to non-blocking I/O
            self._hid_devs.append(dev)
        if not self._hid_devs:
            raise DeviceException("Could not find any HID devices.")
        self._exit_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._trigger_loop,
                                             args=(capture_callback, ))
        self._loop_thread.start()

    def stop_trigger_loop(self):
        self._exit_event.set()

    def _trigger_loop(self, capture_func):
        # Polls all attached HID devices for a press->release event and
        # trigger a capture.
        while True:
            for dev in self._hid_devs:
                # See if there's input
                if dev.read(8):
                    # Wait for key release
                    while not dev.read(8):
                        time.sleep(0.01)
                        continue
                    capture_func()
                else:
                    if self._exit_event.is_set():
                        return
                    time.sleep(0.01)

    def _find_devices(self):
        for candidate in {(x['vendor_id'], x['product_id'])
                          for x in hid.enumerate(0, 0)}:
            try:
                dev = hid.device(*candidate)
            except IOError:
                raise DeviceException("Could not open HID device, please check"
                                      " your permissions on /dev/bus/usb.")
            yield dev

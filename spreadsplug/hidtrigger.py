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

""" Trigger plugin that waits for a key press on any USB HID device. """

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
        """ Find all attached USB HID devices and memorize them for later.

        :param config:  The workflow's configuration
        :type config:   :py:class:`confit.ConfigView`
        """
        self._logger = logging.getLogger('spreadsplug.hidtrigger')
        self._logger.debug("Initializing HidTrigger plugin")
        self._hid_devs = []
        for dev in self._find_devices():
            self._logger.debug("Found HID device: {0}".format(dev))
            self._hid_devs.append(dev)
        if not self._hid_devs:
            self._logger.warning("Could not find any HID devices.")

    def start_trigger_loop(self, capture_callback):
        """ Launch the triggering loop in a background thread.

        :param capture_callback:    Callback for triggering a capture
        :type capture_callback:     function
        """
        if not self._hid_devs:
            self._logger.warning("Not starting trigger loop since there are "
                                 "no HID devices.")
            return

        self._exit_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._trigger_loop,
                                             args=(capture_callback, ))
        self._logger.debug("Starting trigger loop")
        self._loop_thread.start()

    def stop_trigger_loop(self):
        """ Stop the triggering loop and its thread. """
        if self._exit_event is None:
            # Return if no loop thread is running
            return
        self._logger.debug("Stopping trigger loop")
        self._exit_event.set()
        self._loop_thread.join()

    def _trigger_loop(self, capture_func):
        """ Poll all USB HID devices for a press->release event and trigger a
            capture.

        :param capture_func:    Callback for triggering a capture
        :type capture_func:     function
        """
        while not self._exit_event.is_set():
            for dev in self._hid_devs:
                # See if there's input
                if dev.read(8):
                    # Wait for key release
                    while not dev.read(8):
                        time.sleep(0.01)
                        continue
                    try:
                        capture_func()
                    except Exception as e:
                        self._logger.error(
                            "Error occured when invoking capture function.")
                        self._logger.exception(e)
                else:
                    time.sleep(0.01)

    def _find_devices(self):
        """ Find all attached USB HID devices.

        :returns:   All devices found
        :rtype:     Generator that yields :py:class:`hidapi.Device`
        """
        for candidate in hidapi.enumerate():
            try:
                dev = hidapi.Device(candidate, blocking=False)
            except IOError:
                raise DeviceException("Could not open HID device, please check"
                                      " your permissions on /dev/bus/usb.")
            yield dev

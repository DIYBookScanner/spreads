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

""" Trigger plugin that triggers in a configurable interval. """

from __future__ import unicode_literals

import logging
import threading
import time

from spreads.config import OptionTemplate
from spreads.plugin import HookPlugin, TriggerHooksMixin

logger = logging.getLogger('spreadsplug.intervaltrigger')


class IntervalTrigger(HookPlugin, TriggerHooksMixin):
    __name__ = 'intervaltrigger'

    _loop_thread = None
    _exit_event = None

    @classmethod
    def configuration_template(cls):
        return {'interval': OptionTemplate(5.0, "Interval between captures"
                                                " (in seconds)")}

    def start_trigger_loop(self, capture_callback):
        """ Launch the triggering loop in a background thread.

        :param capture_callback:    Callback for triggering a capture
        :type capture_callback:     function
        """
        logger.debug("Starting event loop")
        self._exit_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._trigger_loop,
                                             args=(capture_callback, ))
        self._loop_thread.start()

    def stop_trigger_loop(self):
        """ Stop the triggering loop and its thread. """
        if self._exit_event:
            logger.debug("Stopping event loop")
            self._exit_event.set()
        if self._loop_thread:
            self._loop_thread.join()

    def _trigger_loop(self, capture_func):
        """ Read interval from configuration and run a loop that captures every
            time the interval has elapsed.

        :param capture_func:    Callback for triggering a capture
        :type capture_func:     function
        """
        interval = self.config['interval'].get(float)
        while True and interval > 0.0:
            sleep_time = 0
            while sleep_time < interval:
                if self._exit_event.is_set():
                    return
                time.sleep(0.01)
                sleep_time += 0.01
            capture_func()

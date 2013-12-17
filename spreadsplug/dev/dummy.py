# -*- coding: utf-8 -*-
import logging

from spreads.plugin import DevicePlugin, DeviceFeatures

# NOTE: Ugly global variable to track how often we've been instantiated
num_instances = 0


class DummyDevice(DevicePlugin):
    """ Plugin for dummy device. For development purposes only.

    """

    features = (DeviceFeatures.TWO_DEVICES,)

    @classmethod
    def configuration_template(cls):
        return {}

    @classmethod
    def match(cls, device):
        global num_instances
        if num_instances < 2:
            num_instances += 1
            return True

    def __init__(self, config, device):
        global num_instances
        num_instances += 1
        self.target_page = 'odd' if num_instances == 1 else 'even'
        self.logger = logging.getLogger(
            'DummyDevice[{0}]'.format(self.target_page))

    def set_target_page(self, target_page):
        self.target_page = target_page

    def prepare_capture(self, path):
        self.logger.info("Preparing capture for path '{0}'".format(path))

    def capture(self, path):
        self.logger.info("Capturing image into '{0}'".format(path))

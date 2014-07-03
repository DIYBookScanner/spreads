# -*- coding: utf-8 -*-
import logging
import os
import shutil
import time

from spreads.config import OptionTemplate
from spreads.plugin import DevicePlugin, DeviceFeatures
from spreads.vendor.pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
TEST_IMGS = {'even': BASE_DIR / '../../tests/data/even.jpg',
             'odd':  BASE_DIR / '../../tests/data/odd.jpg'}


class DummyDevice(DevicePlugin):
    """ Plugin for dummy device. For development purposes only.

    """
    __name__ = 'dummy'

    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    @classmethod
    def configuration_template(cls):
        tmpl = super(DummyDevice, cls).configuration_template()
        tmpl['test'] = OptionTemplate(1337, "A test value")
        tmpl['super'] = OptionTemplate(['foo', 'bar'], "An advanced option",
                                       True, True)
        return tmpl

    @classmethod
    def yield_devices(cls, config):
        return [cls(config, None, 'even'), cls(config, None, 'odd')]

    def __init__(self, config, device, target_page):
        self.target_page = target_page
        super(DummyDevice, self).__init__(config, device)
        self.logger = logging.getLogger(
            'DummyDevice[{0}]'.format(self.target_page))
        self.logger.debug("Instantiation completed.")

    def connected(self):
        return True

    def set_target_page(self, target_page):
        self.target_page = target_page

    def prepare_capture(self, path):
        self.logger.info("Preparing capture for path '{0}'".format(path))
        self.logger.debug(self.config.flatten())
        time.sleep(3)

    def capture(self, path):
        self.logger.info("Capturing image into '{0}'".format(path))
        time.sleep(1)
        self.logger.debug(self.config['test'].get())
        shutil.copyfile(unicode(TEST_IMGS[self.target_page]),
                        unicode(path))

    def finish_capture(self):
        self.logger.info("Finishing capture")

    def update_configuration(self, updated):
        pass

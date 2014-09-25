# -*- coding: utf-8 -*-
import logging
import os
import time
import urllib2

from jpegtran import JPEGImage
from wand.drawing import Drawing
from wand.image import Image

from spreads.config import OptionTemplate
from spreads.plugin import DeviceDriver, DeviceFeatures
from spreads.vendor.pathlib import Path


class DummyDevice(DeviceDriver):
    """ Plugin for dummy device. For development purposes only.

    """
    __name__ = 'dummy'

    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA,
                DeviceFeatures.CAN_DISPLAY_TEXT)

    @classmethod
    def configuration_template(cls):
        tmpl = super(DummyDevice, cls).configuration_template()
        tmpl['test'] = OptionTemplate(1337, "A test value")
        tmpl['super'] = OptionTemplate(['foo', 'bar'], "An advanced option",
                                       True, True)
        tmpl['depends'] = OptionTemplate(0, "A dependant option",
                                         depends={'device': {'super': 'bar'}})
        return tmpl

    @classmethod
    def yield_devices(cls, config):
        return [cls(config, None, 'even'), cls(config, None, 'odd')]

    def __init__(self, config, device, target_page):
        base_path = Path(os.path.expanduser('~/.config/spreads'))
        self._test_imgs = {
            'even': base_path / 'even.jpg',
            'odd': base_path / 'odd.jpg'
        }
        if any(not p.exists() for p in self._test_imgs.values()):
            for target, img_path in self._test_imgs.items():
                with img_path.open('wb') as fp:
                    fp.write(urllib2.urlopen(
                        "http://jbaiter.de/files/{0}.jpg".format(target)
                    ).read())
        self.target_page = target_page
        super(DummyDevice, self).__init__(config, device)
        self.logger = logging.getLogger(
            'DummyDevice[{0}]'.format(self.target_page))
        self.logger.debug("Instantiation completed.")

    def connected(self):
        return True

    def set_target_page(self, target_page):
        self.target_page = target_page

    def prepare_capture(self):
        self.logger.info("Preparing capture for dummy device '{0}'"
                         .format(self.target_page))
        self.logger.debug(self.config.flatten())
        time.sleep(3)

    def capture(self, path):
        self.logger.info("Capturing image into '{0}'".format(path))
        self.logger.debug(self.config['test'].get())
        with Drawing() as draw:
            fpath = unicode(self._test_imgs[self.target_page])
            with Image(filename=fpath) as img:
                draw.font_size = 240
                draw.text(img.width/2, img.height/2, path.name)
                draw(img)
                img.save(filename=unicode(path))
        img = JPEGImage(fname=unicode(path))
        aspect = float(img.width)/img.height
        img.exif_thumbnail = img.downscale(320, int(320/aspect))
        img.save(unicode(path))

    def finish_capture(self):
        time.sleep(5)
        self.logger.info("Finishing capture")

    def update_configuration(self, updated):
        pass

    def show_textbox(self, msg):
        print "DISPLAY ON {0} device:\n{1}".format(self.target_page, msg)

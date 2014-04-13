# -*- coding: utf-8 -*-
import logging
import os
import tempfile
import hashlib

from jpegtran import JPEGImage

from spreads.config import OptionTemplate
from spreads.plugin import DevicePlugin, DeviceFeatures

import piggyphoto as pp


class GPhoto2CameraDevice(DevicePlugin):
    """ Plugin for digital cameras communicating via raw PTP.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    target_page = None
    _cli_flags = None
    _gphoto2_buildnum = None

    @classmethod
    def configuration_template(cls):
        conf = super(GPhoto2CameraDevice, cls).configuration_template()
        conf.update(
            {'iso': OptionTemplate(u"Auto", "The ISO value"),
             'shutter_speed': OptionTemplate(
                 u"1/25", "The shutter speed as a fraction"),
             'aperture': OptionTemplate(
                 u"5.6", "The shutter speed as an f-stop"),
             'shoot_raw': OptionTemplate(False, "Shoot in RAW format (DNG)")
             })
        return conf

    @classmethod
    def yield_devices(cls, config):
        """ Search for usable devices, yield one at a time

        :param config:  spreads configuration
        :type config:   spreads.config.ConfigView

        """
        pil = pp.portInfoList()
        for name, path in pp.cameraList(autodetect=True).toList():
            pi = pil.get_info(pil.lookup_path(path))
            cam = pp.camera(autoInit=False)
            cam.port_info = pi
            cam.init()
            yield cls(config, cam)

    def __init__(self, config, camera):
        """ Set connection information and try to obtain target page.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param camera:  camera device
        :type camera:   `camera <http://github.com/piggyphoto>`

        """
        self.logger = logging.getLogger('GPhoto2Camera')
        self._camera = camera
        self.config = config

        try:
            self.target_page = config['target_page'][self._camera.config['status']['serialnumber'].value].get()
        except:
            self.target_page = None

        self.logger = logging.getLogger('GPhoto2Camera[{0}]'
                                        .format(self.target_page))

    def connected(self):
        try:
            self._camera.config
            return True
        except:
            return False

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        # Map this in the spreads config keyed by the camera serial number.
        # We can't use the approach taken by CHDKCameraDevice, because most PTP cameras don't support writing
        # files via PTP.
        self.config['target_page'][self._camera.config['status']['serialnumber'].value].set(target_page)

    def prepare_capture(self, path):
        shutter_speed = self.config["shutter_speed"].get()
        shoot_raw = self.config['shoot_raw'].get(bool)
        aperture = self.config['aperture'].get()

        print "setting ", self.config['iso'].get(), self.config['shutter_speed'].get(), self.config['aperture'].get()

        cfg = self._camera.config
        cfg['imgsettings']['iso'].value = str(self.config['iso'].get())

        if self.config['shoot_raw'].get(bool):
            format = 'RAW'
        else:
            format = 'Large Fine JPEG'
        cfg['imgsettings']['imageformat'].value = format
        cfg['imgsettings']['imageformatsd'].value = format

        if cfg['capturesettings']['shutterspeed']:
            cfg['capturesettings']['shutterspeed'].value = str(self.config['shutter_speed'].get())
        else:
            print("Skipping shutter_speed config due to camera mode ({})".format(cfg['capturesettings']['autoexposuremode']))

        if cfg['capturesettings']['aperture']:
            cfg['capturesettings']['aperture'].value = str(self.config['aperture'].get())
        else:
            print("Skipping aperture config due to camera mode ({})".format(cfg['capturesettings']['autoexposuremode']))

        self._camera.config = cfg

    def finish_capture(self):
        pass

    def get_preview_image(self):
        fpath = tempfile.mkstemp()[1]
        self._camera.capture_preview(fpath)
        with open(fpath, 'rb') as fp:
            data = fp.read()
        os.remove(fpath)
        return data

    def capture(self, path):
        shoot_raw = self.config['shoot_raw'].get(bool)

        # TODO: support choosing jpg size
        # TODO: support choosing sraw vs raw
        # TODO: support capturing raw + jpeg

        extension = 'cr2' if shoot_raw else 'jpg' # TODO: choose raw extension based on camera vendor
        local_path = "{0}.{1}".format(path, extension)

        self._camera.capture_image(local_path)

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        img = JPEGImage(local_path)
        if self.target_page == 'odd':
            img.exif_orientation = 6  # -90°
        else:
            img.exif_orientation = 8  # 90°
        img.save(local_path)

    def _acquire_focus(self):
        return 'not supported yet'

    def _set_focus(self):
        pass
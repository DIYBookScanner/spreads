# -*- coding: utf-8 -*-
import logging
import os
import tempfile

from jpegtran import JPEGImage

from spreads.config import OptionTemplate
from spreads.plugin import DevicePlugin, DeviceFeatures

import piggyphoto as pp


class GPhoto2CameraDevice(DevicePlugin):
    """ Plugin for digital cameras communicating via raw PTP.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    target_page = None

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
            logger = logging.getLogger('GPhoto2Camera')
            logger.debug("Connecting to camera {} at {}".format(name, path))
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
            serialnumber = self._camera.config['status']['serialnumber'].value
            self.target_page = config['target_page'][serialnumber].get()
        except:
            self.target_page = None

        self.logger = logging.getLogger('GPhoto2Camera[{0}]'
                                        .format(self.target_page))

    def connected(self):
        try:
            # check if we're connected by accessing the config, which is
            # backed by a getter function that attempts to retrieve the
            # config from the camera (and throws libgphoto2error if unable
            # to communicate with it).
            self._camera.config
            return True
        except pp.libgphoto2error:
            return False

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        # Map this in the spreads config keyed by the camera serial number.
        # We can't use the approach taken by CHDKCameraDevice, because most
        # PTP cameras don't support writing files via PTP.
        serialnumber = self._camera.config['status']['serialnumber'].value
        self.config['target_page'][serialnumber].set(target_page)

    def prepare_capture(self, path):
        iso = str(self.config['iso'].get())
        shoot_raw = self.config['shoot_raw'].get(bool)
        shutter_speed = str(self.config["shutter_speed"].get())
        aperture = str(self.config['aperture'].get())

        cfg = self._camera.config
        mode = cfg['capturesettings']['autoexposuremode']

        self.logger.debug("Camera mode: {}".format(mode))
        self.logger.debug(
            "Setting iso={}, shutter_speed={}, aperture={}, raw={}"
            .format(iso, shutter_speed, aperture, shoot_raw))

        cfg['imgsettings']['iso'].value = iso

        if shoot_raw:
            format = 'RAW'
        else:
            format = 'Large Fine JPEG'
        cfg['imgsettings']['imageformat'].value = format
        cfg['imgsettings']['imageformatsd'].value = format

        if cfg['capturesettings']['shutterspeed']:
            cfg['capturesettings']['shutterspeed'].value = shutter_speed
        else:
            self.logger.debug(
                "Skipping shutter_speed config due to camera mode ({})"
                .format(mode))

        if cfg['capturesettings']['aperture']:
            cfg['capturesettings']['aperture'].value = aperture
        else:
            self.logger.debug(
                "Skipping aperture config due to camera mode ({})"
                .format(mode))

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
        # TODO: choose raw extension based on camera vendor

        extension = 'cr2' if shoot_raw else 'jpg'
        local_path = "{0}.{1}".format(path, extension)

        self._camera.capture_image(local_path)

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        img = JPEGImage(local_path)
        upside_down = self.config["upside_down"].get(bool)
        if self.target_page == 'odd':
            img.exif_orientation = 5 if upside_down else 6  # -90°
        else:
            img.exif_orientation = 7 if upside_down else 8  # 90°
        img.save(local_path)

    def _acquire_focus(self):
        raise NotImplementedError

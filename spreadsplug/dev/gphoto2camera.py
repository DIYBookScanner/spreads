# -*- coding: utf-8 -*-
import logging

from jpegtran import JPEGImage

from spreads.config import OptionTemplate
from spreads.plugin import DeviceDriver, DeviceFeatures

import gphoto2


class GPhoto2CameraDevice(DeviceDriver):
    """ Plugin for digital cameras communicating via raw PTP.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    target_page = None

    @classmethod
    def configuration_template(cls):
        # TODO: The basic problem that prevents us from supporting more
        # configuration values is that in gphoto2, the available options
        # are only known when the device is already initialized, which
        # is not possible since this is ia @classmethod.
        # We also cannot have the user specify a specific gphoto2 driver,
        # since at the time this method is called, not even the configuration
        # is loaded.
        # The best way to proceed is probably to determine a superset of
        # configuration values that are of interest to spreads users and
        # map from those to the driver's specific options.
        # At first we will likely only support ptp2
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
        for cam in gphoto2.list_cameras():
            yield cls(config, cam)

    def __init__(self, config, camera):
        """ Set connection information and try to obtain target page.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param camera:  camera device
        :type camera:   :py:class:`gphoto2.Camera`

        """
        self.logger = logging.getLogger('GPhoto2Camera')
        self._camera = camera
        self.config = config

        try:
            self._serial_number = self._camera.status.serialnumber
            self.target_page = config['target_page'][self._serial_number].get()
        except:
            self.target_page = None

        self.logger = logging.getLogger('GPhoto2Camera[{0}]'
                                        .format(self.target_page))

    def connected(self):
        try:
            return self._camera.status is not None
        except gphoto2.errors.GPhoto2Error:
            return False

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        # Map this in the spreads config keyed by the camera serial number.
        # We can't use the approach taken by CHDKCameraDevice, because most
        # PTP cameras don't support writing files via PTP.
        self.config['target_page'][self._serialnumber].set(target_page)

    def prepare_capture(self):
        iso = str(self.config['iso'].get())
        shoot_raw = self.config['shoot_raw'].get(bool)
        shutter_speed = str(self.config["shutter_speed"].get())
        aperture = str(self.config['aperture'].get())

        cfg = self._camera.config
        mode = cfg['capturesettings']['autoexposuremode'].value

        self.logger.debug("Camera mode: {}".format(mode))
        self.logger.debug(
            "Setting iso={}, shutter_speed={}, aperture={}, raw={}"
            .format(iso, shutter_speed, aperture, shoot_raw))

        cfg['imgsettings']['iso'].set(iso)

        if shoot_raw:
            format = 'RAW'
        else:
            format = 'Large Fine JPEG'
        cfg['imgsettings']['imageformat'].set(format)
        cfg['imgsettings']['imageformatsd'].set(format)

        if cfg['capturesettings']['shutterspeed']:
            cfg['capturesettings']['shutterspeed'].set(shutter_speed)
        else:
            self.logger.debug(
                "Skipping shutter_speed config due to camera mode ({})"
                .format(mode))

        if cfg['capturesettings']['aperture']:
            cfg['capturesettings']['aperture'].set(aperture)
        else:
            self.logger.debug(
                "Skipping aperture config due to camera mode ({})"
                .format(mode))

    def finish_capture(self):
        pass

    def get_preview_image(self):
        return self._camera.get_preview()

    def capture(self, path):
        shoot_raw = self.config['shoot_raw'].get(bool)

        # TODO: support choosing jpg size
        # TODO: support choosing sraw vs raw
        # TODO: support capturing raw + jpeg
        # TODO: choose raw extension based on camera vendor

        extension = 'cr2' if shoot_raw else 'jpg'
        local_path = "{0}.{1}".format(path, extension)

        imgdata = self._camera.capture()

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        img = JPEGImage(blob=imgdata)
        upside_down = self.config["upside_down"].get(bool)
        if self.target_page == 'odd':
            img.exif_orientation = 8 if upside_down else 6  # -90°
        else:
            img.exif_orientation = 6 if upside_down else 8  # 90°
        img.save(local_path)

    def update_configuration(self, updated):
        # TODO: Implement
        pass

    def _acquire_focus(self):
        raise NotImplementedError

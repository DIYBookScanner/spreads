# -*- coding: utf-8 -*-
import logging

from jpegtran import JPEGImage

from spreads.plugin import DeviceDriver, DeviceFeatures

import gphoto2


class GPhoto2CameraDevice(DeviceDriver):
    """ Plugin for digital cameras communicating via raw PTP.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    target_page = None

    @classmethod
    def configuration_template(cls):
        # TODO: The basic problem that prevents us from supporting any
        # configuration values is that in gphoto2, the available options are
        # only known when the device is already initialized, which is not
        # possible since this is ia @classmethod.  We also cannot have the user
        # specify a specific gphoto2 driver, since at the time this method is
        # called, not even the configuration is loaded.  The best way to
        # proceed is probably to determine a superset of configuration values
        # that are of interest to spreads users and map from those to the
        # driver's specific options.  At first we will likely only support ptp2
        # TODO: Another significant problem is that even for cameras that
        # are supported by the ptp2 driver, the names and possible values
        # of the configuration widgets can differ drastically. A possible
        # solution for this would be to create subclasses for various,
        # known-to-work camera models that expose their own configuration
        # templates and implement the configuration-related methods
        # themselves.
        return super(GPhoto2CameraDevice, cls).configuration_template()

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
        logging.getLogger('libgphoto2').setLevel(logging.CRITICAL)
        self._camera = camera
        self.config = config
        self._serial_number = unicode(self._camera.status.serialnumber)
        try:
            self.target_page = config['target_page'][self._serial_number].get()
        except:
            self.target_page = None

        self.logger = logging.getLogger('GPhoto2Camera[{0}]'
                                        .format(self.target_page))

    def connected(self):
        try:
            return bool(self._camera.supported_operations)
        except gphoto2.errors.GPhoto2Error as e:
            self.logger.error(e)
            return False

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        # Map this in the spreads config keyed by the camera serial number.
        # We can't use the approach taken by CHDKCameraDevice, because most
        # PTP cameras don't support writing files via PTP.
        self.config['target_page'][self._serial_number].set(target_page)

    def prepare_capture(self):
        pass

    def finish_capture(self):
        pass

    def get_preview_image(self):
        return self._camera.get_preview()

    def capture(self, path):
        imgdata = self._camera.capture()

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        img = JPEGImage(blob=imgdata)
        upside_down = self.config["upside_down"].get(bool)
        if self.target_page == 'odd':
            img.exif_orientation = 8 if upside_down else 6  # -90°
        else:
            img.exif_orientation = 6 if upside_down else 8  # 90°
        img.save(unicode(path))

    def update_configuration(self, updated):
        pass

    def _acquire_focus(self):
        raise NotImplementedError

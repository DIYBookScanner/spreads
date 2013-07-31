# -*- coding: utf-8 -*-
import logging
import os
import time
from fractions import Fraction
from math import log

import pexif
import pyptpchdk
from PIL import Image

from spreads.plugin import DevicePlugin
from spreads.util import DeviceException


class PTPDevice(object):
    """ Small wrapper class around pyptpchdk for easier access to PTP
        functions.

    """
    STATUS_RUN = 1
    STATUS_MSG = 2

    def __init__(self, usbdevice):
        self._orientation = None
        self.logger = logging.getLogger('PTPDevice')
        self._device = pyptpchdk.PTPDevice(usbdevice.bus, usbdevice.address)

    def __del__(self):
        del(self._device)

    def execute_lua(self, script, wait=True, get_result=False, timeout=256):
        """ Executes a Lua script on the camera.

        :param script: The Lua script
        :type script: str
        :param wait: Wait for the script to complete
        :type wait: bool
        :param get_result: Return the script's return value
        :type get_result: bool
        :return: The script's return value (tuple) if get_result was True,
                 or None

        """
        # Wrap the script in return if the script doesn't return by itself
        if get_result and not "return" in script:
            script = "return({0})".format(script)
        retries = 0
        while retries < 4:
            self.logger.debug("Executing script: \"{0}\"".format(script))
            try:
                script_id = self._device.chdkExecLua(script)
            except pyptpchdk.PTPError as exc:
                self.logger.warn("Script raised an error, retrying in 10s...")
                time.sleep(10)
                if retries == 3:
                    raise exc
                retries += 1
                continue
            script_status = None
            if not wait:
                return
            # Wait for the script to complete
            loops = 0
            while loops < timeout and script_status not in (1, 2):
                loops += 1
                script_status = self._device.chdkScriptStatus(script_id)
                time.sleep(0.01)
            if not script_status:
                self.logger.warn("Script timed out, retrying...")
                retries += 1
            else:
                break
        if get_result:
            return self._get_messages(script_id)
        else:
            self._flush_messages()
            return

    def _get_messages(self, script_id):
        msg = None
        retvals = []
        # Get all messages returned by the script
        while not retvals or msg[2] != 0:
            time.sleep(0.01)
            msg = self._device.chdkReadScriptMessage()
            if msg[1] == 1:
                raise DeviceException("Lua error: {0}".format(msg[0]))
            if msg[2] == 0:
                continue
            if msg[2] != script_id:
                self.logger.warn(
                    "Script IDs did not match. Expected \"{0}\","
                    " got \"{1}\", ignoring".format(script_id, msg[2])
                )
                self.logger.debug("Message (type {0}) was: {1}"
                                  .format(msg[1], msg[0]))
                continue
            self.logger.debug("Camera returned: {0}".format(msg[0]))
            retvals.append(msg[0])
        # NOTE: Just to be safe...
        time.sleep(0.25)
        # Return a tuple containing all of the messages
        return tuple(retvals)

    def _flush_messages(self):
        msg = (None, None, None)
        while msg[2] != 0:
            time.sleep(0.01)
            msg = self._device.chdkReadScriptMessage()

    def get_orientation(self):
        # NOTE: CHDK doesn't seem to be able to write the EXIF owner to the
        #       camera's internal flash memory, so we have to use this
        #       workaround.
        if self._orientation:
            return self._orientation
        try:
            orientation = self.execute_lua("""
                file=io.open('A/OWN.TXT')
                content=file:read()
                file:close()
                return content
                """, get_result=True)[0].lower()
            self.logger.debug("Orientation is: \"{0}\"".format(orientation))
            self.logger = logging.getLogger('PTPDevice[{0}]'
                                            .format(orientation))
            self._orientation = orientation
            return orientation
        except DeviceException as e:
            self.logger.warn("Could not get orientation, reason: {0}"
                         .format(e.message))
            return None

    def set_orientation(self, orientation):
        self.execute_lua("""
            file=io.open('A/OWN.TXT', 'w')
            file:write("{0}")
            file:close()
        """.format(orientation.upper()), get_result=False)
        self._orientation = orientation

    def get_image_list(self):
        img_path = self.execute_lua("get_image_dir()")[0]
        file_list = [os.path.join(img_path, x.split("\t")[1])
                     for x in (self.execute_lua("os.listdir(\"{0}\")"
                               .format(img_path))[0].split("\n")[:-1])]
        return file_list

    def download_image(self, camera_path, local_path):
        self.logger.debug("Downloading \"{0}\"".format(local_path))
        self._device.chdkDownload(camera_path, local_path)
        img = pexif.JpegFile.fromFile(local_path)
        if self._orientation == 'left':
            exif_orientation = 8  # 90°
        else:
            exif_orientation = 6  # -90°
        img.exif.primary.Orientation = [exif_orientation]
        img.writeFile(local_path)

    def delete_image(self, camera_path):
        self.execute_lua("os.remove(\"{0}\")".format(camera_path))
        time.sleep(0.5)

    def download_all_images(self, path):
        for fpath in self.get_image_list():
            self.download_image(
                fpath,
                os.path.join(path, os.path.basename(fpath)))

    def delete_all_images(self):
        for fpath in self.get_image_list():
            self.delete_image(fpath)

    def get_preview_image(self, viewport=True, ui_overlay=False):
        flags = 0
        if viewport:
            flags |= pyptpchdk.LiveViewFlags.VIEWPORT
        if ui_overlay:
            flags |= pyptpchdk.LiveViewFlags.BITMAP
        data = self._device.chdkGetLiveData(flags)
        img = data['viewport']
        # FIXME: Use wand for this, once the new version is out that supports
        #        raw RGB data.
        return Image.fromstring('RGB', (img['width'], img['height']),
                                img['data'])


class CHDKCameraDevice(DevicePlugin):
    """ Plugin for digital cameras running the CHDK firmware.

    """
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--sensitivity', '-S', dest="sensitivity", type=int,
            metavar="<int>", help="ISO sensitivity")
        parser.add_argument(
            "--shutter-speed", '-s', dest="shutter_speed", type=unicode,
            metavar="<int/float/str>", help="Shutter speed")
        parser.add_argument(
            "--zoom-level", "-z", dest="zoom_level", type=int, metavar="<int>",
            help="Zoom level")

    def __init__(self, config, device):
        """ Set connection information and try to obtain orientation.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  USB device to use for the object
        :type device:   `usb.core.Device <http://github.com/walac/pyusb>`_

        """
        self.config = config['device']
        self._device = PTPDevice(device)
        self.orientation = self._device.get_orientation()

    def set_orientation(self, orientation):
        """ Set the device orientation.

        :param orientation: The orientation name
        :type orientation:  unicode in (u"left", u"right")

        """
        self._device.set_orientation(orientation)
        self.orientation = orientation

    def delete_files(self):
        self._device.delete_all_images()

    def download_files(self, path):
        self._device.download_all_images(path)

    def list_files(self):
        return self._device.get_image_list()

    def prepare_capture(self):
        self._set_record_mode()
        time.sleep(0.25)
        self._set_zoom(self.config['zoom_level'].get(int))
        self._set_sensitivity(self.config['sensitivity'].get(int))
        self._disable_flash()
        self._disable_ndfilter()

    def capture(self):
        """ Shoot a picture. """
        # Set ISO
        self._set_sensitivity(self.config['sensitivity'].get(int))
        # Set shutter speed (has to be set for every shot)
        # Calculate TV96 value from shutter_speed
        shutter_float = (float(Fraction(self.config['shutter_speed']
                         .get(unicode))))
        tv96_value = -96*log(shutter_float)/log(2)
        # Round to nearest multiple of 32
        tv96_value = int(32*round(tv96_value/32))
        self._device.execute_lua("set_tv96_direct({0})".format(tv96_value))
        self._device.execute_lua("shoot()", get_result=False)

    def _set_record_mode(self):
        """ Put the camera in record mode. """
        self._device.execute_lua("switch_mode_usb(1)")

    def _get_zoom(self):
        """ Get current zoom level.

        :returns: int -- the current zoom level

        """
        return self._device.execute_lua("get_zoom()")[0]

    def _set_zoom(self, level):
        """ Set zoom level.

        :param level: The zoom level to be used
        :type level:  int

        """
        available_levels = self._device.execute_lua("get_zoom_steps()")[0]
        if not level in available_levels:
            raise DeviceException("Level outside of supported range!")
        self._device.execute_lua('set_zoom({0})'.format(level))

    def _disable_flash(self):
        """ Disable the camera's flash. """
        self._device.execute_lua("set_prop(16, 2)")

    def _set_sensitivity(self, value=80):
        """ Set the camera's ISO value.

        :param iso_value: The ISO value in ISO/ASA format
        :type iso-value:  int

        """
        self._device.execute_lua("set_iso_mode({0})".format(value))

    def _disable_ndfilter(self):
        """ Disable the camera's ND Filter. """
        self._device.execute_lua("set_nd_filter(2)")

    def _play_sound(self, sound_num):
        """ Plays one of the following sounds:
                0 = startup sound
                1 = shutter sound
                2 = button press sound
                3 = selftimer
                4 = short beep
                5 = af (auto focus) confirmation
                6 = error beep
        """
        self._device.execute_lua("play_sound({0})".format(sound_num))


class CanonA2200CameraDevice(CHDKCameraDevice):
    """ Canon A2200 driver.

        Works around some quirks of that CHDK port.

    """
    ISO_TO_APEX = {
        80: 373,
    }

    def __init__(self, config, device):
        super(CanonA2200CameraDevice, self).__init__(config, device)
        self.logger = logging.getLogger(
            'CanonA2200CameraDevice[{0}]'.format(self.orientation))

    @classmethod
    def match(cls, device):
        matches = (hex(device.idVendor) == "0x4a9"
                   and hex(device.idProduct) == "0x322a")
        return matches

    def _set_zoom(self, level):
        """ Set zoom level.

            The A2200 currently has a bug, where setting the zoom level
            directly via set_zoom crashes the camera quite frequently, so
            we work around that by simulating button presses.

        :param level: The zoom level to be used
        :type level:  int

        """
        if level > 7:
            raise Exception("Zoom level {0} exceeds the camera's range!"
                            .format(level))
        zoom = None
        while zoom != level:
            zoom = self._get_zoom()
            self.logger.debug("Zoom for {0}: {1}".format(self.orientation, zoom))
            if zoom > level:
                self._device.execute_lua('click("zoom_out")')
            elif zoom < level:
                self._device.execute_lua('click("zoom_in")')
            time.sleep(1)

    def _set_sensitivity(self, value=80):
        """ Set the camera's ISO value.

            `set_iso_mode` doesn't seem to work, so we have to use set_sv96.
            Problem is that I've not yet figured out the conversion formula
            from ISO to the ASA/APEX value required for this function, which,
            from what I understand, has to be determined for every camera
            separately...

        :param iso_value: The ISO value in ISO/ASA format
        :type iso-value:  int

        """
        iso_value = self.config['sensitivity'].get(int)
        try:
            sv96_value = CanonA2200CameraDevice.ISO_TO_APEX[iso_value]
        except KeyError:
            raise Exception("The desired ISO value is not supported.")
        self._device.execute_lua("set_sv96({0})".format(sv96_value))

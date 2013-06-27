import logging
import os
import subprocess
import time

from fractions import Fraction
from math import log

from spreads.plugin import DevicePlugin
from spreads.util import SpreadsException, DeviceException


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
        self._device = device
        self.orientation = (self._gphoto2(["--get-config",
                                           "/main/settings/ownername"])
                            .split("\n")[-2][9:] or None)

    def _gphoto2(self, args):
        """ Call gphoto2.

        :param args:  The arguments for gphoto2
        :type args:   list
        :returns:     unicode -- combined stdout and stderr of the gphoto2
                                    process.

        """
        cmd = (["gphoto2", "--port", "usb:{0:03},{1:03}".format(
                self._device.bus, self._device.address)]
               + args)
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except OSError:
            raise SpreadsException("gphoto2 executable could not be found,"
                                   "please install!")
        return out

    def _ptpcam(self, command):
        """ Call ptpcam to execute command on device.

        :param command: The CHDK command to execute on the device
        :type command:  unicode
        :returns:       unicode -- combined stdout and stderr of the ptpcam
                                    process

        """
        cmd = ["ptpcam", "--dev={0:03}".format(self._device.address),
               "--bus={0:03}".format(self._device.bus),
               "--chdk='{0}'".format(command)]
        logging.debug("Running " + " ".join(cmd))
        try:
            out = subprocess.check_output(" ".join(cmd), shell=True,
                                          stderr=subprocess.STDOUT)
        except OSError:
            raise SpreadsException("ptpcam executable could not be found,"
                                   " please install!")
        return out

    def set_orientation(self, orientation):
        """ Set the device orientation.

        :param orientation: The orientation name
        :type orientation:  unicode in (u"left", u"right")

        """
        self._gphoto2(["--set-config",
                       "/main/settings/ownername={0}".format(orientation)])
        self.orientation = orientation

    def delete_files(self):
        try:
            self._gphoto2(["--recurse", "-D", "A/store00010001/DCIM/"])
        except subprocess.CalledProcessError:
            # For some reason gphoto2 throws an error despite everything going
            # well...
            pass

    def download_files(self, path):
        cur_dir = os.getcwd()
        os.chdir(path)
        try:
            self._gphoto2(["--recurse", "-P", "A/store00010001/DCIM/"])
        except subprocess.CalledProcessError:
            # For some reason gphoto2 throws an error despite everything going
            # well...
            pass
        os.chdir(cur_dir)

    def prepare_capture(self):
        self._set_record_mode()
        time.sleep(1)
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
        self._ptpcam("luar set_tv96_direct({0})".format(tv96_value))
        self._ptpcam("luar shoot()")

    def _set_record_mode(self):
        """ Put the camera in record mode. """
        self._ptpcam("mode 1")

    def _get_zoom(self):
        """ Get current zoom level.

        :returns: int -- the current zoom level

        """
        return int(self._ptpcam('luar get_zoom()').split()[1][-1])

    def _set_zoom(self, level):
        """ Set zoom level.

        :param level: The zoom level to be used
        :type level:  int

        """
        available_levels = int(self._ptpcam('luar get_zoom_steps()')
                               .split()[1][-1])
        if not level in available_levels:
            raise CameraException("Level outside of supported range!")
        self._ptpcam('lua set_zoom({0})'.format(level))

    def _disable_flash(self):
        """ Disable the camera's flash. """
        self._ptpcam("luar set_prop(16, 2)")

    def _set_sensitivity(self, value=80):
        """ Set the camera's ISO value.

        :param iso_value: The ISO value in ISO/ASA format
        :type iso-value:  int

        """
        self._ptpcam('lua set_iso_mode({0})'.format(value))

    def _disable_ndfilter(self):
        """ Disable the camera's ND Filter. """
        self._ptpcam("luar set_nd_filter(2)")

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
        self._ptpcam("lua play_sound({1})".format(sound_num))


class CanonA2200CameraDevice(CHDKCameraDevice):
    """ Canon A2200 driver.

        Works around some quirks of that CHDK port.

    """
    ISO_TO_APEX = {
        80: 373,
    }

    @classmethod
    def match(cls, device):
        matches = (hex(device.idVendor) == "0x4a9"
                   and hex(device.idProduct) == "0x322a")
        logging.debug("Trying to match %s,%s: %s" % (hex(device.idVendor),
                                                     hex(device.idProduct),
                                                     matches))
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
            logging.debug("Zoom for {0}: {1}".format(self.orientation, zoom))
            if zoom > level:
                self._ptpcam('luar click("zoom_out")')
            elif zoom < level:
                self._ptpcam('luar click("zoom_in")')
            time.sleep(0.25)

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
        self._ptpcam("luar set_sv96({0})".format(sv96_value))

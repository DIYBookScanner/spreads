# -*- coding: utf-8 -*-
import logging
import os
import re
import subprocess
import tempfile
from fractions import Fraction
from itertools import chain


from spreads.plugin import DevicePlugin, PluginOption, DeviceFeatures
from spreads.util import DeviceException


class CHDKPTPException(Exception):
    pass


class CHDKCameraDevice(DevicePlugin):
    """ Plugin for digital cameras running the CHDK firmware.

    """

    features = (DeviceFeatures.PREVIEW, DeviceFeatures.TWO_DEVICES)

    orientation = None
    _cli_flags = None
    _chdk_buildnum = None
    _can_remote = False
    _zoom_steps = 0

    @classmethod
    def configuration_template(cls):
        conf = {'two_devices': PluginOption(True,
                                            "Use two cameras for shooting"),
                'reverse_spreads': PluginOption(
                    False, "When shooting with two devices, flip the target"
                    "book spreads (odd<->even)"),
                'sensitivity': PluginOption(80, "The ISO sensitivity value"),
                'shutter_speed': PluginOption(
                    u"1/25", "The shutter speed as a fraction"),
                'zoom_level': PluginOption(3, "The default zoom level"),
                'dpi': PluginOption(300, "The capturing resolution"),
                'shoot_raw': PluginOption(False, "Shoot in RAW format (DNG)"),
                'chdkptp_path': PluginOption(
                    u"/usr/local/lib/chdkptp",
                    "Path to CHDKPTP binary/libraries"),
                }
        return conf

    @classmethod
    def match(cls, device):
        cfg = device.get_active_configuration()[(0, 0)]
        matches = (hex(cfg.bInterfaceClass) == "0x6"
                   and hex(cfg.bInterfaceSubClass) == "0x1")
        return matches

    def __init__(self, config, device):
        """ Set connection information and try to obtain orientation.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  USB device to use for the object
        :type device:   `usb.core.Device <http://github.com/walac/pyusb>`_

        """
        self.logger = logging.getLogger('ChdkCamera')
        self._chdkptp_path = config["chdkptp_path"].get(unicode)
        self._sensitivity = config["sensitivity"].get(int)
        self._shutter_speed = float(Fraction(config["shutter_speed"]
                                    .get(unicode)))
        self._zoom_level = config['zoom_level'].get(int)
        self._dpi = config['dpi'].get(int)
        self._shoot_raw = config['shoot_raw'].get(bool)

        self._cli_flags = []
        self._cli_flags.append("-c-d={0:03} -b={1:03}".format(
                               device.address, device.bus))
        self._chdk_buildnum = (self._execute_lua("get_buildinfo()",
                                                 get_result=True)
                               ["build_revision"])
        # PTP remote shooting is available starting from SVN r2927
        self._can_remote = self._chdk_buildnum >= 2927
        self._zoom_steps = self._execute_lua("get_zoom_steps()",
                                             get_result=True)
        if config["two_devices"].get(bool):
            try:
                self.orientation = self._get_orientation()
            except ValueError:
                raise DeviceException("Orientation could not be determined, "
                                      "please run 'spread configure' to "
                                      "configure your devices.")
        self.logger = logging.getLogger('ChdkCamera[{0}]'
                                        .format(self.orientation))

    def set_orientation(self, orientation):
        """ Set the device orientation.

        :param orientation: The orientation name
        :type orientation:  unicode in (u"odd", u"even")

        """
        tmp_handle = tempfile.mkstemp(text=True)
        os.write(tmp_handle[0], orientation.upper()+"\n")
        self._run("upload {0} \"OWN.TXT\"".format(tmp_handle[1]))
        self.orientation = orientation

    def prepare_capture(self, path):
        # Try to put into record mode
        if not os.path.exists(path):
            os.mkdir(path)
        if not os.path.exists(os.path.join(path, self.orientation)):
            os.mkdir(os.path.join(path, self.orientation))
        try:
            self._run("rec")
        except CHDKPTPException as e:
            self.logger.debug(e)
            self.logger.info("Camera already seems to be in recording mode")
        self._set_zoom(self._zoom_level)
        # Disable flash
        self._execute_lua("while(get_flash_mode()<2) do click(\"right\") end")
        # Disable ND filter
        self._execute_lua("set_nd_filter(2)")
        #self._lock_focus()

    def get_preview_image(self):
        fpath = tempfile.mkstemp()[1]
        cmd = "dumpframes -count=1 -nobm -nopal"
        self._run("{0} {1}".format(cmd, fpath))
        with open(fpath, 'rb') as fp:
            data = fp.read()
        os.remove(fpath)
        return data

    def capture(self, path):
        path = os.path.join(path, self.orientation)
        if self._can_remote:
            cmd = ("remoteshoot -tv={0} -isomode={1} {2} {3}"
                   .format(self._shutter_speed, self._sensitivity,
                           "-dng" if self._shoot_raw else "", path))
        else:
            cmd = ("shoot -tv={0} -isomode={1} -dng={2} -rm -dl {3}"
                   .format(self._shutter_speed, self._sensitivity,
                           int(self._shoot_raw), path))
        self._run(cmd)
        # TODO: If we are in two-device mode, set EXIF orientation with
        #       'exiftool', according to orientation

    def _run(self, *commands):
        cmd_args = list(chain((os.path.join(self._chdkptp_path, "chdkptp"),),
                              self._cli_flags,
                              ("-e{0}".format(cmd) for cmd in commands)))
        env = {'LUA_PATH': os.path.join(self._chdkptp_path, "lua/?.lua")}
        self.logger.debug("Calling chdkptp with arguments: {0}"
                          .format(cmd_args))
        output = (subprocess.check_output(cmd_args, env=env,
                                          stderr=subprocess.STDOUT)
                  .splitlines())
        # Filter out connected message
        output = [x for x in output if not x.startswith('connected:')]
        # Check for possible CHDKPTP errors
        if any('ERROR' in x for x in output):
            raise CHDKPTPException("\n".join(output))
        return output

    def _execute_lua(self, script, wait=True, get_result=False, timeout=256):
        if get_result and not "return" in script:
            script = "return({0})".format(script)
        cmd = "luar" if wait else "lua"
        output = self._run("{0} {1}".format(cmd, script))
        if not get_result:
            return
        output = [x for x in output if x.find(":return:")][0]
        return self._parse_lua_output(output)

    def _parse_table(self, data):
        values = dict(re.findall(r'([\w_]+?)=(\d+|".*?"),', data[6:]))
        for k, v in values.iteritems():
            if v.startswith('"') and v.endswith('"'):
                values[k] = v.strip('"')  # String
            else:
                values[k] = int(v)  # Integer
        return values

    def _parse_lua_output(self, output):
        ret_val = re.match(r'^\d+:return:(.*)', output).group(1)
        if ret_val.startswith('table:'):
            return self._parse_table(ret_val)  # Table
        elif ret_val.startswith("'"):
            return ret_val.strip("'")  # String
        else:
            return int(ret_val)  # Integer

    def _get_orientation(self):
        tmp_handle = tempfile.mkstemp(text=True)
        try:
            self._run("download \"OWN.TXT\" {0}".format(tmp_handle[1]))
        except DeviceException:
            raise ValueError("Could not find OWN.TXT")
        with open(tmp_handle[1], 'r') as fp:
            orientation = fp.readline().strip().lower()
        os.remove(tmp_handle[1])
        if not orientation:
            raise ValueError("Could not read OWN.TXT")
        return orientation

    def _set_zoom(self, level):
        if level >= self._zoom_steps:
            raise Exception("Zoom level {0} exceeds the camera's range!"
                            " (max: {1})".format(level, self._zoom_steps-1))
        self._execute_lua("set_zoom({0})".format(level), wait=False)


class CanonA2200CameraDevice(CHDKCameraDevice):
    """ Canon A2200 driver.

        Works around some quirks of that CHDK port.

    """
    def __init__(self, config, device):
        print "Instantiating device..."
        super(CanonA2200CameraDevice, self).__init__(config, device)
        if self.orientation is not None:
            self.logger = logging.getLogger(
                'CanonA2200CameraDevice[{0}]'.format(self.orientation))
        else:
            self.logger = logging.getLogger('CanonA2200CameraDevice')

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
        if level >= self._zoom_steps:
            raise DeviceException(
                "Zoom level {0} exceeds the camera's range!"
                " (max: {1})".format(level, self._zoom_steps-1))
        zoom = self._execute_lua("get_zoom()", get_result=True)
        if zoom < level:
            self._execute_lua("while(get_zoom()<3) do click(\"zoom_in\") end",
                              wait=True)
        elif zoom > level:
            self._execute_lua("while(get_zoom()>3) do click(\"zoom_out\") end",
                              wait=True)

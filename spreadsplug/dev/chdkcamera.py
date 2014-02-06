# -*- coding: utf-8 -*-
import logging
import os
import re
import subprocess
import tempfile
import time
from fractions import Fraction
from itertools import chain

import usb
from jpegtran import JPEGImage
from spreads.vendor.pathlib import Path

from spreads.plugin import DevicePlugin, PluginOption, DeviceFeatures
from spreads.util import DeviceException


class CHDKPTPException(Exception):
    pass


class CHDKCameraDevice(DevicePlugin):
    """ Plugin for digital cameras running the CHDK firmware.

    """

    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA)

    target_page = None
    _cli_flags = None
    _chdk_buildnum = None
    _can_remote = False
    _zoom_steps = 0

    @classmethod
    def configuration_template(cls):
        conf = super(CHDKCameraDevice, cls).configuration_template()
        conf.update(
            {'sensitivity': PluginOption(80, "The ISO sensitivity value"),
             'shutter_speed': PluginOption(
                 u"1/25", "The shutter speed as a fraction"),
             'zoom_level': PluginOption(3, "The default zoom level"),
             'dpi': PluginOption(300, "The capturing resolution"),
             'shoot_raw': PluginOption(False, "Shoot in RAW format (DNG)"),
             'focus_distance': PluginOption('auto', "Set focus distance"),
             'chdkptp_path': PluginOption(
                 u"/usr/local/lib/chdkptp",
                 "Path to CHDKPTP binary/libraries"),
             })
        return conf

    @classmethod
    def yield_devices(cls, config):
        """ Search for usable devices, yield one at a time

        """
        for dev in usb.core.find(find_all=True):
            cfg = dev.get_active_configuration()[(0, 0)]
            is_match = (hex(cfg.bInterfaceClass) == "0x6"
                        and hex(cfg.bInterfaceSubClass) == "0x1")
            if is_match:
                yield cls(config, dev)

    def __init__(self, config, device):
        """ Set connection information and try to obtain target page.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  USB device to use for the object
        :type device:   `usb.core.Device <http://github.com/walac/pyusb>`_

        """
        self.logger = logging.getLogger('ChdkCamera')
        self._usbport = (device.bus, device.address)
        self._serial_number = (
            usb.util.get_string(device, 256, device.iSerialNumber)
            .strip('\x00'))
        self.logger.debug("Device has serial number {0}"
                          .format(self._serial_number))
        self._chdkptp_path = Path(config["chdkptp_path"].get(unicode))
        self._sensitivity = config["sensitivity"].get(int)
        self._shutter_speed = float(Fraction(config["shutter_speed"]
                                    .get(unicode)))
        self._zoom_level = config['zoom_level'].get(int)
        self._dpi = config['dpi'].get(int)
        self._shoot_raw = config['shoot_raw'].get(bool)
        self._focus_distance = config['focus_distance'].get()

        self._cli_flags = []
        self._cli_flags.append("-c-d={1:03} -b={0:03}".format(*self._usbport))
        self._cli_flags.append("-eset cli_verbose=2")
        self._chdk_buildnum = (self._execute_lua("get_buildinfo()",
                                                 get_result=True)
                               ["build_revision"])
        # PTP remote shooting is available starting from SVN r2927
        self._can_remote = self._chdk_buildnum >= 2927
        self._zoom_steps = self._execute_lua("get_zoom_steps()",
                                             get_result=True)
        try:
            self.target_page = self._get_target_page()
        except:
            self.target_page = None

        self._execute_lua('exit_alt(); set_config_value(291, 0);'
                          'enter_alt();')
        self.logger = logging.getLogger('ChdkCamera[{0}]'
                                        .format(self.target_page))

    def connected(self):
        def match_serial(dev):
            serial = (
                usb.util.get_string(dev, 256, dev.iSerialNumber)
                .strip('\x00'))
            return serial == self._serial_number

        # Check if device is still attached
        unchanged = usb.core.find(bus=self._usbport[0],
                                  address=self._usbport[1],
                                  custom_match=match_serial) is not None
        if unchanged:
            return True
        new_device = usb.core.find(idVendor=0x04a9,  # Canon vendor ID
                                   custom_match=match_serial)
        if new_device is None:
            return False

        self._usbport = (new_device.bus, new_device.address)
        self._cli_flags[0] = ("-c-d={1:03} -b={0:03}".format(*self._usbport))
        return True

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        tmp_handle = tempfile.mkstemp(text=True)
        os.write(tmp_handle[0], target_page.upper()+"\n")
        self._run("upload {0} \"OWN.TXT\"".format(tmp_handle[1]))
        self.target_page = target_page
        os.remove(tmp_handle[1])

    def prepare_capture(self, path):
        # Try to go into alt mode to prevent weird behaviour
        self._execute_lua("enter_alt()")
        # Try to put into record mode
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
        self._set_focus()

    def finish_capture(self):
        # Switch camera back to play mode.
        # This will retract the lens and protect it from dust.
        self._run("play")

    def get_preview_image(self):
        fpath = tempfile.mkstemp()[1]
        cmd = "dumpframes -count=1 -nobm -nopal"
        self._run("{0} {1}".format(cmd, fpath))
        with open(fpath, 'rb') as fp:
            data = fp.read()
        os.remove(fpath)
        return data

    def capture(self, path):
        # NOTE: To obtain the "real" Canon ISO value, we multiply the
        #       "market" value from the config by 0.65.
        #       See core/shooting.c#~l150 in the CHDK source for more details
        if self._can_remote:
            cmd = ("remoteshoot -tv={0} -sv={1} {2} \"{3}\""
                   .format(self._shutter_speed, self._sensitivity*0.65,
                           "-dng" if self._shoot_raw else "", path))
        else:
            cmd = ("shoot -tv={0} -sv={1} -dng={2} -rm -dl \"{3}\""
                   .format(self._shutter_speed, self._sensitivity*0.65,
                           int(self._shoot_raw), path))
        try:
            self._run(cmd)
        except CHDKPTPException as e:
            if 'not in rec mode' in e.message:
                self.prepare_capture(None)
                self.capture(path)
            else:
                self.logger.warn("Capture command failed.")
                P
                raise e

        extension = 'dng' if self._shoot_raw else 'jpg'
        local_path = "{0}.{1}".format(path, extension)
        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        img = JPEGImage(local_path)
        if self.target_page == 'odd':
            img.orientation = 8  # 90°
        else:
            img.orientation = 6  # -90°
        img.save(local_path)

    def show_textbox(self, message):
        messages = message.split("\n")
        script = "\n".join(
            ['screen_width = get_gui_screen_width();',
             'screen_height = get_gui_screen_height();',
             'draw_rect_filled(0, 0, screen_width, screen_height, 256, 256);'] +
            ['draw_string(0, 0+(screen_height/10)*{0}, "{1}", 258, 256);'
             .format(idx, msg) for idx, msg in enumerate(messages, 1)]
        )
        self._execute_lua(script, wait=False, get_result=False)

    def _run(self, *commands):
        cmd_args = list(chain((unicode(self._chdkptp_path / "chdkptp"),),
                              self._cli_flags,
                              ("-e{0}".format(cmd) for cmd in commands)))
        env = {'LUA_PATH': unicode(self._chdkptp_path / "lua/?.lua")}
        self.logger.debug("Calling chdkptp with arguments: {0}"
                          .format(cmd_args))
        output = (subprocess.check_output(cmd_args, env=env,
                                          stderr=subprocess.STDOUT)
                  .splitlines())
        self.logger.debug("Call returned:\n{0}".format(output))
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
        values = dict(re.findall(r'([\w_]+?)=(\d+|".*?"),*', data[6:]))
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
        elif ret_val in ('true', 'false'):
            return ret_val == 'true'
        else:
            return int(ret_val)  # Integer

    def _get_target_page(self):
        tmp_handle = tempfile.mkstemp(text=True)
        try:
            self._run("download \"OWN.TXT\" {0}".format(tmp_handle[1]))
            with open(tmp_handle[1], 'r') as fp:
                target_page = fp.readline().strip().lower()
        except DeviceException:
            raise ValueError("Could not find OWN.TXT")
        finally:
            os.remove(tmp_handle[1])
        if not target_page:
            raise ValueError("Could not read OWN.TXT")
        return target_page

    def _set_zoom(self, level):
        if level >= self._zoom_steps:
            raise ValueError("Zoom level {0} exceeds the camera's range!"
                             " (max: {1})".format(level, self._zoom_steps-1))
        self._execute_lua("set_zoom({0})".format(level), wait=False)

    def _acquire_focus(self):
        """ Acquire auto focus and lock it. """
        self._execute_lua("enter_alt()")
        # Try to put into record mode
        try:
            self._run("rec")
        except CHDKPTPException as e:
            self.logger.debug(e)
            self.logger.info("Camera already seems to be in recording mode")
        self._set_zoom(self._zoom_level)
        self._execute_lua("set_aflock(0)")
        self._execute_lua("press('shoot_half')")
        time.sleep(0.8)
        self._execute_lua("release('shoot_half')")
        time.sleep(0.5)
        return self._execute_lua("get_focus()", get_result=True)

    def _set_focus(self):
        self._execute_lua("set_aflock(0)")
        if self._focus_distance == 'auto':
            return
        self._execute_lua("set_focus({0:.0f})".format(self._focus_distance))
        time.sleep(0.5)
        self._execute_lua("press('shoot_half')")
        time.sleep(0.25)
        self._execute_lua("release('shoot_half')")
        time.sleep(0.25)
        self._execute_lua("set_aflock(1)")


class CanonA2200CameraDevice(CHDKCameraDevice):
    """ Canon A2200 driver.

        Works around some quirks of that CHDK port.

    """
    def __init__(self, config, device):
        super(CanonA2200CameraDevice, self).__init__(config, device)
        if self.target_page is not None:
            self.logger = logging.getLogger(
                'CanonA2200CameraDevice[{0}]'.format(self.target_page))
        else:
            self.logger = logging.getLogger('CanonA2200CameraDevice')

    @classmethod
    def match(cls, device):
        matches = (hex(device.idVendor) == "0x4a9"
                   and hex(device.idProduct) == "0x322a")
        return matches

    def finish_capture(self):
        # Putting the device back into play mode crashes the a2200 with
        # chdk 1.3, this is why we stub it out here.
        pass

    def _set_zoom(self, level):
        """ Set zoom level.

            The A2200 currently has a bug, where setting the zoom level
            directly via set_zoom crashes the camera quite frequently, so
            we work around that by simulating button presses.

        :param level: The zoom level to be used
        :type level:  int

        """
        if level >= self._zoom_steps:
            raise ValueError(
                "Zoom level {0} exceeds the camera's range!"
                " (max: {1})".format(level, self._zoom_steps-1))
        zoom = self._execute_lua("get_zoom()", get_result=True)
        if zoom < level:
            self._execute_lua("while(get_zoom()<{0}) do click(\"zoom_in\") end"
                              .format(level+1),
                              wait=True)
        elif zoom > level:
            self._execute_lua("while(get_zoom()>{0}) "
                              "do click(\"zoom_out\") end".format(level+1),
                              wait=True)

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
from spreads.vendor.pathlib import Path

from spreads.config import OptionTemplate
from spreads.plugin import DevicePlugin, DeviceFeatures
from spreads.util import DeviceException, MissingDependencyException

try:
    from jpegtran import JPEGImage

    def update_exif_orientation(fpath, orientation):
        img = JPEGImage(fpath)
        img.exif_orientation = orientation
        img.save(fpath)
except ImportError:
    import pyexiv2

    def update_exif_orientation(fpath, orientation):
        metadata = pyexiv2.ImageMetadata(fpath)
        metadata.read()
        metadata['Exif.Image.Orientation'] = int(orientation)
        metadata.write()


WHITEBALANCE_MODES = {
    'Auto': 0,
    'Daylight': 1,
    'Cloudy': 2,
    'Tungsten': 3,
    'Fluorescent': 4,
    'Fluorescent H': 5,
    'Custom': 7
}


class CHDKPTPException(Exception):
    pass


class CHDKCameraDevice(DevicePlugin):
    """ Plugin for digital cameras running the CHDK firmware.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA,
                DeviceFeatures.CAN_DISPLAY_TEXT)

    target_page = None
    _cli_flags = None
    _chdk_buildnum = None
    _can_remote = False
    _zoom_steps = 0

    MAX_RESOLUTION = 0
    MAX_QUALITY = 0

    @classmethod
    def configuration_template(cls):
        conf = super(CHDKCameraDevice, cls).configuration_template()
        conf.update(
            {'sensitivity': OptionTemplate(80, "The ISO sensitivity value"),
             'shutter_speed': OptionTemplate(
                 u"1/25", "The shutter speed as a fraction"),
             'zoom_level': OptionTemplate(3, "The default zoom level"),
             'dpi': OptionTemplate(300, "The capturing resolution"),
             'shoot_raw': OptionTemplate(False, "Shoot in RAW format (DNG)",
                                         advanced=True),
             'focus_distance': OptionTemplate(0, "Set focus distance"),
             'monochrome': OptionTemplate(
                 False, "Shoot in monochrome mode (reduces file size)"),
             'whitebalance': OptionTemplate(
                 value=sorted(WHITEBALANCE_MODES),
                 docstring='White balance mode', selectable=True,
                 advanced=True),
             'chdkptp_path': OptionTemplate(u"/usr/local/lib/chdkptp",
                                            "Path to CHDKPTP binary/libraries",
                                            advanced=True),
             })
        return conf

    @classmethod
    def yield_devices(cls, config):
        """ Search for usable devices, yield one at a time

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        """
        SPECIAL_CASES = {
            # (idVendor, idProduct): SpecialClass
            (0x4a9, 0x31ef): QualityFix,  # not r47, but has the same bug
            (0x4a9, 0x3218): QualityFix,
            (0x4a9, 0x3223): QualityFix,
            (0x4a9, 0x3224): QualityFix,
            (0x4a9, 0x3225): QualityFix,
            (0x4a9, 0x3226): QualityFix,
            (0x4a9, 0x3227): QualityFix,
            (0x4a9, 0x3228): QualityFix,
            (0x4a9, 0x3229): QualityFix,
            (0x4a9, 0x322a): A2200,
            (0x4a9, 0x322b): QualityFix,
            (0x4a9, 0x322c): QualityFix,
        }

        # Check if we can find the chdkptp executable
        chdkptp_path = Path(config["chdkptp_path"].get(unicode))
        if not chdkptp_path.exists() or not (chdkptp_path/'chdkptp').exists():
            raise MissingDependencyException(
                "Could not find executable `chdkptp`. Please make sure that "
                "the `chdkptp_path` setting in your `chdkcamera` "
                "configuration points to " "a directory containing chdkptp "
                "and its libraries. Current setting is `{0}`"
                .format(chdkptp_path)
            )

        # only match ptp devices in find_all
        def is_ptp(dev):
            for cfg in dev:
                if usb.util.find_descriptor(cfg, bInterfaceClass=6,
                                            bInterfaceSubClass=1):
                    return True

        for dev in usb.core.find(find_all=True, custom_match=is_ptp):
            ids = (dev.idVendor, dev.idProduct)
            if ids in SPECIAL_CASES:
                yield SPECIAL_CASES[ids](config, dev)
            else:
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
        self.config = config

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

        # Set camera to highest quality
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
        self._set_zoom()
        # Disable ND filter
        self._execute_lua("set_nd_filter(2)")
        self._set_focus()
        self._set_monochrome()
        # Set White Balance mode
        self._set_whitebalance()
        # Disable flash
        self._execute_lua(
            "props = require(\"propcase\")\n"
            "if(get_flash_mode()~=2) then set_prop(props.FLASH_MODE, 2) end")
        # Set Quality
        self._execute_lua("set_prop(require('propcase').QUALITY, {0})"
                          .format(self.MAX_QUALITY))
        self._execute_lua("set_prop(require('propcase').RESOLUTION, {0})"
                          .format(self.MAX_RESOLUTION))

    def _set_monochrome(self):
        if self.config['monochrome'].get(bool):
            rv = self._execute_lua(
                "capmode = require(\"capmode\")\n"
                "return capmode.set(\"SCN_MONOCHROME\")",
                get_result=True
            )
            if not rv:
                self.logger.warn("Monochrome mode not supported on this "
                                 "device, will be disabled.")
                self.config['monochrome'] = False
        else:
            rv = self._execute_lua(
                "capmode = require(\"capmode\")\n"
                "return capmode.set(\"P\")",
                get_result=True
            )

    def finish_capture(self):
        # NOTE: We should retract the lenses to protect them from dust by
        # switching back to play mode (`self._run("play")`), but due to a bug
        # in a majority of CHDK devices, we currently cannot do that, so we
        # just do nothing here. See issue #114 on GitHub for more details
        pass

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
        sensitivity = int(self.config["sensitivity"].get())
        shutter_speed = float(Fraction(self.config["shutter_speed"]
                              .get(unicode)))
        shoot_raw = self.config['shoot_raw'].get(bool)

        # chdkptp expects that there is no file extension, so we temporarily
        # strip it
        noext_path = path.parent/path.stem
        if self._can_remote:
            cmd = ("remoteshoot -tv={0} -sv={1} {2} \"{3}\""
                   .format(shutter_speed, sensitivity*0.65,
                           "-dng" if shoot_raw else "", noext_path))
        else:
            cmd = ("shoot -tv={0} -sv={1} -dng={2} -rm -dl \"{3}\""
                   .format(shutter_speed, sensitivity*0.65,
                           int(shoot_raw), noext_path))
        try:
            self._run(cmd)
        except CHDKPTPException as e:
            if 'not in rec mode' in e.message:
                self.prepare_capture(None)
                self.capture(path)
            else:
                self.logger.error("Capture command failed.")
                raise e
        except Exception as e:
            self.logger.error("Capture command failed.")
            raise e

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        upside_down = self.config["upside_down"].get(bool)
        if self.target_page == 'odd':
            update_exif_orientation(unicode(path), 8 if upside_down else 6)
        else:
            update_exif_orientation(unicode(path), 6 if upside_down else 8)

    def update_configuration(self, updated):
        if 'zoom_level' in updated:
            self._set_zoom()
        if 'focus_distance' in updated:
            self._set_focus()
        if 'whitebalance' in updated:
            self._set_whitebalance()
        if 'monochrome' in updated:
            self._set_monochrome()

    def show_textbox(self, message):
        self._execute_lua("enter_alt()")
        messages = message.split("\n")
        script = [
            'require("drawings");'
            'draw.add("rectf", 0, 0, get_gui_screen_width(), '
            '         get_gui_screen_height(), 256, 256);',
        ]
        script.extend([
            'draw.add("string", 0, 0+(get_gui_screen_height()/10)*{0}, '
            '         "{1}", 258, 256);'
            .format(idx, msg) for idx, msg in enumerate(messages, 1)
        ])
        script.append("draw.overdraw();")
        self._execute_lua("\n".join(script), get_result=True)

    def _run(self, *commands):
        chdkptp_path = Path(self.config["chdkptp_path"].get(unicode))
        cmd_args = list(chain((unicode(chdkptp_path / "chdkptp"),),
                              self._cli_flags,
                              ("-e{0}".format(cmd) for cmd in commands)))
        env = {'LUA_PATH': unicode(chdkptp_path / "lua/?.lua")}
        self.logger.debug("Calling chdkptp with arguments: {0}"
                          .format(cmd_args))
        output = subprocess.check_output(
            cmd_args, env=env, stderr=subprocess.STDOUT,
            close_fds=True  # see http://stackoverflow.com/a/1297785/487903
        ).splitlines()
        self.logger.debug("Call returned:\n{0}".format(output))
        # Filter out connected message
        output = [x for x in output if not x.startswith('connected:')]
        # Check for possible CHDKPTP errors
        if any('ERROR' in x for x in output):
            raise CHDKPTPException("\n".join(output))
        return output

    def _execute_lua(self, script, wait=True, get_result=False, timeout=256):
        if get_result and not "return" in script:
            script = "return{{{0}}}".format(script)
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

    def _set_zoom(self):
        level = int(self.config['zoom_level'].get())
        if level >= self._zoom_steps:
            raise ValueError("Zoom level {0} exceeds the camera's range!"
                             " (max: {1})".format(level, self._zoom_steps-1))
        self._execute_lua("set_zoom({0})".format(level), wait=True)

    def _acquire_focus(self):
        """ Acquire auto focus and lock it. """
        self._execute_lua("enter_alt()")
        # Try to put into record mode
        try:
            self._run("rec")
        except CHDKPTPException as e:
            self.logger.debug(e)
            self.logger.info("Camera already seems to be in recording mode")
        self._set_zoom()
        self._execute_lua("set_aflock(0)")
        self._execute_lua("press('shoot_half')")
        time.sleep(0.8)
        self._execute_lua("release('shoot_half')")
        time.sleep(0.5)
        return self._execute_lua("get_focus()", get_result=True)

    def _get_focus(self):
        result = int(self.config['focus_distance'].get())
        focus_odd = int(self.config['focus_odd'].get())
        if self.target_page == "odd" and int(focus_odd) != 0:
            result = focus_odd
        return result

    def _set_focus(self):
        self.logger.info("Running default focus")
        focus_distance = self._get_focus()
        if int(focus_distance) == 0:
            self._execute_lua("set_aflock(0)")
        else:
            self._execute_lua("press('shoot_half')")
            time.sleep(1.0)
            self._execute_lua("click('left')")
            time.sleep(0.25)
            self._execute_lua("release('shoot_half')")
            time.sleep(0.25)
            self._execute_lua("set_focus({0:.0f})".format(focus_distance))

    def _set_whitebalance(self):
        value = WHITEBALANCE_MODES.get(self.config['whitebalance'].get())
        self._execute_lua("set_prop(require('propcase').WB_MODE, {0})"
                          .format(value))


class A2200(CHDKCameraDevice):
    """ Canon A2200 driver.

        Works around some quirks of that CHDK port.

    """
    MAX_RESOLUTION = 0
    MAX_QUALITY = 1

    def __init__(self, config, device):
        super(A2200, self).__init__(config, device)
        if self.target_page is not None:
            self.logger = logging.getLogger(
                'A2200Device[{0}]'.format(self.target_page))
        else:
            self.logger = logging.getLogger('A2200Device')

class QualityFix(CHDKCameraDevice):
    """ Fixes a bug that prevents remote capture with the highest resolution
    and quality from succeeding.  See this CHDK forum post for more details:
    http://chdk.setepontos.com/index.php?topic=4338.msg111318#msg111318
    """
    MAX_RESOLUTION = 0
    MAX_QUALITY = 1

    def __init__(self, config, device):
        super(QualityFix, self).__init__(config, device)
        if self.target_page is not None:
            self.logger = logging.getLogger(
                'QualityFixDevice[{0}]'.format(self.target_page))
        else:
            self.logger = logging.getLogger('QualityFixDevice')

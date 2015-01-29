# -*- coding: utf-8 -*-
import logging
import os
import tempfile
import time
from fractions import Fraction

import chdkptp

from spreads.config import OptionTemplate
from spreads.plugin import DeviceDriver, DeviceFeatures, DeviceException

try:
    from jpegtran import JPEGImage

    def update_exif_orientation(data, orientation):
        img = JPEGImage(blob=data)
        img.exif_orientation = orientation
        return img.as_blob()
except ImportError:
    import pyexiv2

    def update_exif_orientation(data, orientation):
        metadata = pyexiv2.ImageMetadata.from_buffer(data)
        metadata.read()
        metadata['Exif.Image.Orientation'] = int(orientation)
        metadata.write()
        return metadata.buffer


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


class CHDKCameraDevice(DeviceDriver):
    """ Plugin for digital cameras running the CHDK firmware.

    """
    features = (DeviceFeatures.PREVIEW, DeviceFeatures.IS_CAMERA,
                DeviceFeatures.CAN_DISPLAY_TEXT,
                DeviceFeatures.CAN_ADJUST_FOCUS)

    target_page = None
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
             'monochrome': OptionTemplate(
                 False, "Shoot in monochrome mode (reduces file size)"),
             'whitebalance': OptionTemplate(
                 value=sorted(WHITEBALANCE_MODES),
                 docstring='White balance mode', selectable=True,
                 advanced=True),
             })
        return conf

    @classmethod
    def yield_devices(cls, config):
        """ Search for usable devices, yield one at a time

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        """
        SPECIAL_CASES = {  # noqa
            # (idVendor, idProduct): SpecialClass
            (0x4a9, 0x31ef): QualityFix,  # not r47, but has the same bug
            (0x4a9, 0x3218): QualityFix,
            (0x4a9, 0x3223): A3300,
            (0x4a9, 0x3224): QualityFix,
            (0x4a9, 0x3225): QualityFix,
            (0x4a9, 0x3226): QualityFix,
            (0x4a9, 0x3227): QualityFix,
            (0x4a9, 0x3228): QualityFix,
            (0x4a9, 0x3229): QualityFix,
            (0x4a9, 0x322a): QualityFix,
            (0x4a9, 0x322b): QualityFix,
            (0x4a9, 0x322c): QualityFix,
        }

        for info in chdkptp.list_devices():
            ids = (info.vendor_id, info.product_id)
            if ids in SPECIAL_CASES:
                yield SPECIAL_CASES[ids](config, chdkptp.ChdkDevice(info))
            else:
                yield cls(config, chdkptp.ChdkDevice(info))

    def __init__(self, config, device):
        """ Set connection information and try to obtain target page.

        :param config:  spreads configuration
        :type config:   spreads.confit.ConfigView
        :param device:  Device to use for the object
        :type device:   :py:class:`chdkptp.ChdkDevice`

        """
        self._device = device
        self.logger = logging.getLogger("{0}[{1}]".format(
            self.__class__.__name__,
            self._device.info.serial_num[:4]))
        self.config = config
        self._chdk_buildnum = self._device.lua_execute(
            "return get_buildinfo()")['build_revision']
        # PTP remote shooting is available starting from SVN r2927
        self._can_remote = self._chdk_buildnum >= 2927
        self._zoom_steps = self._device.lua_execute("return get_zoom_steps()")
        try:
            self.target_page = self._get_target_page()
        except:
            self.target_page = None

        # Set camera to highest quality
        self._device.lua_execute('exit_alt(); set_config_value(291, 0);'
                                 'enter_alt();', do_return=False)

    def connected(self):
        if self._device.is_connected:
            return True
        try:
            self._device.reconnect()
        except (chdkptp.lua.PTPError, chdkptp.lua.lupa.LuaError):
            return False
        return True

    @property
    def focus(self):
        val = self.config['focus_distance'].get()
        if ',' in val:
            idx = 0 if self.target_page == 'odd' else 1
            val = val.split(',')[idx]
        return int(val)

    def set_target_page(self, target_page):
        """ Set the device target page.

        :param target_page: The target page name
        :type target_page:  unicode in (u"odd", u"even")

        """
        tmp_handle = tempfile.mkstemp(text=True)
        os.write(tmp_handle[0], target_page.upper()+"\n")
        self._device.upload_file(tmp_handle[1], "OWN.TXT")
        self.target_page = target_page
        os.remove(tmp_handle[1])

    def prepare_capture(self):
        # Try to go into alt mode to prevent weird behaviour
        self._device.lua_execute("enter_alt()")
        self._device.switch_mode('record')
        self._set_zoom()
        # Disable ND filter
        self._device.lua_execute("set_nd_filter(2)")
        self._set_monochrome()
        self._set_whitebalance()
        # Disable flash
        self._device.lua_execute(
            "props = require(\"propcase\")\n"
            "if(get_flash_mode()~=2) then set_prop(props.FLASH_MODE, 2) end",
            do_return=False)
        # Set Quality
        self._device.lua_execute("set_prop(require('propcase').QUALITY, {0})"
                                 .format(self.MAX_QUALITY))
        self._device.lua_execute(
            "set_prop(require('propcase').RESOLUTION, {0})"
            .format(self.MAX_RESOLUTION))
        self._set_focus()

    def _set_monochrome(self):
        if self.config['monochrome'].get(bool):
            rv = self._device.lua_execute(
                "capmode = require(\"capmode\")\n"
                "return capmode.set(\"SCN_MONOCHROME\")")
            if not rv:
                self.logger.warn("Monochrome mode not supported on this "
                                 "device, will be disabled.")
                self.config['monochrome'] = False
        else:
            rv = self._device.lua_execute(
                "capmode = require(\"capmode\")\n"
                "return capmode.set(\"P\")")

    def finish_capture(self):
        # NOTE: We should retract the lenses to protect them from dust by
        # switching back to play mode (`self._run("play")`), but due to a bug
        # in a majority of CHDK devices, we currently cannot do that, so we
        # just do nothing here. See issue #114 on GitHub for more details
        pass

    def get_preview_image(self):
        return next(self._device.get_frames())

    def capture(self, path):
        # NOTE: To obtain the "real" Canon ISO value, we multiply the
        #       "market" value from the config by 0.65.
        #       See core/shooting.c#~l150 in the CHDK source for more details
        options = {
            'shutter_speed': chdkptp.util.shutter_to_tv96(
                float(Fraction(self.config["shutter_speed"].get(unicode)))),
            'market_iso': int(self.config["sensitivity"].get()),
            'dng': self.config['shoot_raw'].get(bool),
            'stream': self._can_remote,
            'download_after': not self._can_remote,
            'remove_after': not self._can_remote
        }

        if self._device.mode != 'record':
            self.prepare_capture()
        retried = False
        while True:
            try:
                data = self._device.shoot(**options)
                if data:
                    break
                elif not retried:
                    self.logger.warn("No data received, retrying shot.")
                    retried = True
                else:
                    raise DeviceException("No data received from camera.")
            except Exception as e:
                if not retried:
                    self.logger.warn("Error during capture, retrying shot.")
                    self._device.reconnect()
                    retried = True
                    continue
                self.logger.error("Capture command failed.")
                self.logger.exception(e)
                raise e

        # Set EXIF orientation
        self.logger.debug("Setting EXIF orientation on captured image")
        upside_down = self.config["upside_down"].get(bool)
        if self.target_page == 'odd':
            data = update_exif_orientation(data, 8 if upside_down else 6)
        else:
            data = update_exif_orientation(data, 6 if upside_down else 8)
        with path.open('wb') as fp:
            fp.write(data)

    def update_configuration(self, updated):
        if 'zoom_level' in updated:
            self._set_zoom()
        if any(x in updated for x in ('focus_distance', 'focus_mode')):
            self._set_focus()
        if 'whitebalance' in updated:
            self._set_whitebalance()
        if 'monochrome' in updated:
            self._set_monochrome()

    def show_textbox(self, message):
        self._device.lua_execute("enter_alt()")
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
        self._device.lua_execute("\n".join(script), do_return=False)

    def _get_target_page(self):
        try:
            return self._device.download_file('OWN.TXT').strip().lower()
        except chdkptp.lua.PTPError:
            raise ValueError("Could not read OWN.TXT")

    def _set_zoom(self):
        level = int(self.config['zoom_level'].get())
        if level >= self._zoom_steps:
            raise ValueError("Zoom level {0} exceeds the camera's range!"
                             " (max: {1})".format(level, self._zoom_steps-1))
        self._device.lua_execute("set_zoom({0})".format(level))

    def _acquire_focus(self):
        """ Acquire auto focus and lock it. """
        self._device.lua_execute("enter_alt()")
        self._device.switch_mode('record')
        self._set_zoom()
        self._device.lua_execute("set_aflock(0)")
        self._device.lua_execute("press('shoot_half')")
        time.sleep(0.8)
        self._device.lua_execute("release('shoot_half')")
        time.sleep(0.5)
        return self._device.lua_execute("return get_focus()")

    def _set_focus(self):
        focus_mode = self.config['focus_mode'].get()
        self.logger.info("Setting focus to mode '{0}'".format(focus_mode))
        if focus_mode == "autofocus_all":
            self._device.lua_execute("set_aflock(0)", do_return=False)
        elif focus_mode == "autofocus_initial":
            self._device.lua_execute(
                "press('shoot_half');"
                "sleep(1000);"
                "release('shoot_half');"
                "set_aflock(1);", do_return=False)
        else:
            focus_distance = self.config['focus_distance'].get()
            self._device.lua_execute(
                "press('shoot_half');"
                "sleep(1000);"
                "click('left');"
                "set_aflock(1);"
                "release('shoot_half');", do_return=False)
            time.sleep(0.25)
            self._device.lua_execute("set_focus({0:.0f})"
                                     .format(focus_distance))

    def _set_whitebalance(self):
        value = WHITEBALANCE_MODES.get(self.config['whitebalance'].get())
        self._device.lua_execute("set_prop(require('propcase').WB_MODE, {0})"
                                 .format(value))


class QualityFix(CHDKCameraDevice):
    """ Fixes a bug that prevents remote capture with the highest resolution
    and quality from succeeding.  See this CHDK forum post for more details:
    http://chdk.setepontos.com/index.php?topic=4338.msg111318#msg111318
    """
    MAX_RESOLUTION = 0
    MAX_QUALITY = 1


class A3300(QualityFix):
    """ Canon A3300 driver.

    Works around the fact that this camera does not support remote shooting
    in JPEG format even on very recent revisions of CHDK.
    """

    @property
    def _can_remote(self):
        # NOTE: Remote shooting only works with RAW/DNG.
        return (self._chdk_buildnum >= 2927 and
                self.config['shoot_raw'].get(bool))

    @_can_remote.setter
    def _can_remote(self, val):
        pass

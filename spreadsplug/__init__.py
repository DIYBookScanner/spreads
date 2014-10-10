# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
spreadsplug package

This package contains all of the plugins and device drivers that are shipped
with the application and supported by the spreads developers themselves.

In alphabetical order:

:py:mod:`spreadsplug.autorotate`
    Postprocessing plugin to rotate captured images according to their EXIF
    orientation tag.

:py:mod:`spreadsplug.dev.chdkcamera`
    Driver for Canon cameras with the CHDK firmware.

:py:mod:`spreadsplug.dev.gphoto2`
    Driver for cameras supported by libgphoto2

:py:mod:`spreadsplug.dev.dummy`
    Dummy driver that implements the driver interface and just spits out one
    of the two test images. Intended for rapid development, not for general
    usage.

:py:mod:`spreadsplug.djvubind`
    Output plugin to compress and bundle images (and OCRed text) into a single
    DJVU file using the `djvubind` utility.

:py:mod:`spreadsplug.gui`
    Subcommand plugin for a graphical wizard using Qt (via the PySide bindings)

:py:mod:`spreadsplug.hidtrigger`
    Trigger plugin to initiate a capture from USB HID devices (like foot-pedals
    or gamepads)

:py:mod:`spreadsplug.intervaltrigger`
    Trigger plugin to initiate a capture in a configurable interval.

:py:mod:`spreadsplug.pdfbeads`
    Output plugin to compress and bundle images (and OCRed text) into a single
    PDF file using the `pdfbeads` utility.

:py:mod:`spreadsplug.scantailor`
    Postprocesing plugin to put captured images through the ScanTailor
    application.

:py:mod:`spreadsplug.tesseract`
    Postprocessing plugin to perform optical character recognition on the
    images, using the `tesseract` application

:py:mod:`spreadsplug.web`
    Subcommand plugin for a RESTful HTTP API (implemented with Flask and
    Tornado) and a single-page JavaScript web application (implemented with
    ReactJS)
"""

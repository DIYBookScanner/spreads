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

:Py:mod:`spreadsplug.web`
    Subcommand plugin for a RESTful HTTP API (implemented with Flask and
    Tornado) and a single-page JavaScript web application (implemented with
    ReactJS)
"""

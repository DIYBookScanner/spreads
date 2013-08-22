Plugins
*******

*spreads* comes with a variety of plugins pre-installed, most of which are
activated by default (except for :ref:`djvubind`). Plugins perform their
actions at several designated points in the workflow. They can also add options
and arguments to the command-line switches of each command.

subcommand plugins
==================
These plugins add additional commands to the *spread* application. This way,
plugins can implement additional workflow steps or provide alternative interfaces
for the application.

gui
---
Launches a graphical interface to the workflow. The steps are the same as
with the :ref:`CLI wizard <cli_tutorial>`, additionally a small thumbnail of every
captured image is shown during the capture process. Requires an installation
of the *PySide* packages. Refer to the :ref:`GUI tutorial <gui_tutorial>`
for more information.

*download* plugins
==================
These provide functionality that is executed after the files have been
downloaded from the devices. They are only allowed to change the images in
ways that preserve all of their original data (i.e. they are allowed to rotate
the images while preserving all of the metadata, but not to scale them).

combine
-------
Combines images from the left and right devices to a single folder.

.. option:: --first-page FIRST_PAGE, -fp FIRST_PAGE

   Only active when the ``combine`` plugin is active (it is enabled by default).
   Select which devices has the first page (default: left). Use this when
   you have changed your setup (e.g. switched to paperback scanning mode
   on the DIY BookScanner).

.. _postproc_plugs:

*postprocess* plugins
======================
An extension to the *postprocess* command. Performs one or more actions that
either modify the captured images or generate a different output.

.. _plug_autorotate:

autorotate
----------
Automatically rotates the images according to their device of origin. By
default this means -90° for the left device and 90° for the right device, but
this can be set to +/- 180° by specifying the :option:`rotate-inverse
<--rotate-inverse, -ri>` option.

.. option:: --rotate-inverse, -ri

   By default, *spreads* will rotate your images either by +/- 90 degrees,
   depending on their device of origin. With this setting, you can switch
   these values, in case you scanned your book upside down. Often used in
   combination with the ``--first-page`` switch of the ``download`` command.

colorcorrect
------------
Automatically fixes white balance for your scanned images. To use it, enable
it in the configuration, set the RGB values for your grey cards and ensure
that the first two images you take are of your grey cards.

.. _plug_scantailor:

scantailor
----------
Automatically generate a ScanTailor configuration file for your scanned book
and generate output images from it. After the configuration has been generated,
you can adjust it in the ScanTailor UI, that will be opened automatically,
unless you specified the :option:`auto <--auto -a>` option. The generation of
the output images will run on all CPU cores in parallel.

.. option:: --auto, -a

   Run ScanTailor on on autopilot and do not require and user input during
   postprocessing. This skips the step where you can manually adjust the
   ScanTailor configuration.

.. option:: --page-detection, -pd

   By default, ScanTailor will use content boundaries to determine what to
   include in its output. With this option, you can tell it to use the page
   boundaries instead.

.. _plug_tesseract:

tesseract
---------
Perform optical character recognition on the scanned pages, using the
*tesseract* application, that has to be installed in order for the plugin to
work. For every recognized page, a HTML document in hOCR format will be written
to *project-directory/done*. These files can be used by the output plugins
to include the recognized text.

.. option:: --language LANGUAGE, -l LANGUAGE

   Tell tesseract which language to use for OCR. You can get a list of all
   installed languages on your system by running ``tesseract --list-langs``.
   The default is 'eng' (English).

.. _output_plugs:

*output* plugins
================
An extension to the *out* command. Generates one or more output files from
the scanned and postprocessed images. Writes its output to *project-directory/done*.

.. _plug_pdfbeads:

pdfbeads
--------
Generate a PDF file from the scanned and postprocessed images, using the
*pdfbeads* tool. If OCR has been performed before, the PDF will include a
hidden text layer with the recognized text.

.. _djvubind:

djvubind
--------
Generate a DJVU file from the scanned and postprocessed images, using the
*djvubind* tool.

.. seealso:: :ref:`Extending spreads functionality <extend_commands>`

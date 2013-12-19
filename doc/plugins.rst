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

.. _postproc_plugs:

*postprocess* plugins
======================
An extension to the *postprocess* command. Performs one or more actions that
either modify the captured images or generate a different output.

.. _plug_autorotate:

autorotate
----------
Automatically rotates the images according to their device of origin. By
default this means -90° for odd pages and 90° for even pages, but these can
be set to arbitrary values by specifying the :option:`rotate-even<--rotate-even>`
or :option:`rotate-odd<--rotate-odd>` options. You probably want to stick to
multiples of 90°.

.. option:: --rotate-even

   Change rotation for images from even book pages (default: 90°)

.. option:: --rotate-odd

   See above, only for odd pages (default: -90°)


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

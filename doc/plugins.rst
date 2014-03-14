Plugins
*******

*spreads* comes with a variety of plugins pre-installed. Plugins perform their
actions at several designated points in the workflow. They can also add
specify options that can be set from one of the interfaces.

subcommand plugins
==================
These plugins add additional commands to the *spread* application. This way,
plugins can implement additional workflow steps or provide alternative interfaces
for the application.

gui
---
Launches a graphical interface to the workflow. The steps are the same as with
the :ref:`CLI wizard <cli_tutorial>`, additionally a small thumbnail of every
captured image is shown during the capture process. Requires an installation of
the *PySide* packages. Refer to the :ref:`GUI tutorial <gui_tutorial>` for more
information.

web
---
Launches the spread web interface that offers a REST-ish API with which you
can control the application from any HTTP client. It also includes a
client-side JavaScript application that can be used from any recent browser
(Firefox or Chrome recommended). Fore more details, consult the `Web interface
documentation <web_doc>` and the `REST API documentation <rest_api>`

.. option:: --database <path>

   Location of workflow database, by default `~/.config/spreads/workflows.db`

.. option:: --standalone-device

   Enable standalone mode. This option can be used for devices that are
   dedicated to scanning (e.g. a RaspberryPi that runs spreads and nothing
   else). At the moment the only additional feature it enables is the ability
   to shutdown the device from the web interface and REST API.

.. option:: --debug

   Run the application debugging mode.

.. option:: --project-dir <path>

   Location where workflow files are stored. By default this is `~/scans`.

.. _postproc_plugs:

*postprocess* plugins
======================
An extension to the *postprocess* command. Performs one or more actions that
either modify the captured images or generate a different output.

.. _plug_autorotate:

autorotate
----------
Automatically rotates the images according to their device of origin.

.. _plug_scantailor:

scantailor
----------
Automatically generate a ScanTailor configuration file for your scanned book
and generate output images from it. After the configuration has been generated,
you can adjust it in the ScanTailor UI, that will be opened automatically,
unless you specified the :option:`auto <--auto -a>` option. The generation of
the output images will run on all CPU cores in parallel.

.. option:: --autopilot

   Run ScanTailor on on autopilot and do not require and user input during
   postprocessing. This skips the step where you can manually adjust the
   ScanTailor configuration.

.. option:: --detection <content/page> [default: content]

   By default, ScanTailor will use content boundaries to determine what to
   include in its output. With this option, you can tell it to use the page
   boundaries instead.

.. option:: --no-content

   Disable content detection step.

.. option:: --rotate

   Enable rotation step.

.. option:: --no-deskew

   Do not deskew images.

.. option:: --no-split-pages

   Do not split pages.

.. option:: --no-auto-margins

   Disable automatically detect margins.


.. _plug_tesseract:

tesseract
---------
Perform optical character recognition on the scanned pages, using the
*tesseract* application, that has to be installed in order for the plugin to
work. For every recognized page, a HTML document in hOCR format will be written
to *project-directory/done*. These files can be used by the output plugins
to include the recognized text.

.. option:: --language LANGUAGE

   Tell tesseract which language to use for OCR. You can get a list of all
   installed languages on your system by running `spread capture --help`.

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

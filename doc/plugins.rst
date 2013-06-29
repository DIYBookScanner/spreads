Plugins
*******

*spreads* comes with a variety of plugins pre-installed, most of which are
activated by default (except for :ref:`djvubind`). Plugins perform their
actions at several designated points in the workflow. They can also add options
and arguments to the command-line switches of each command.

*download* plugins
==================
These provide functionality that is executed after the files have been
downloaded from the devices. They are only allowed to change the images in
ways that preserve all of their original data (i.e. they are allowed to rotate
the images while preserving all of the metadata, but not to scale them).

combine
-------
Combines images from the left and right images to a single folder.

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
   depending on their device of origin. With this setting, you can change
   this value to +/- 180 degrees, in case you scanned your book upside down.

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

.. _plug_pdfbeads:

pdfbeads
--------
Generate a PDF file from the scanned and postprocessed images, using the
*pdfbeads* tool.

.. _djvubind:

djvubind
--------
Generate a DJVU file from the scanned and postprocessed images, using the
*djvubind* tool.

.. seealso:: :ref:`Extending spreads functionality <extend_commands>`

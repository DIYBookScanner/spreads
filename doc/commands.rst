Command-Line Interface
**********************

**spread** is *spreads'* command-line interface.

It takes a *command* as its first argument::

    $ spread COMMAND [ARGS...]

All of *spreads'* functionality is accesible via the following commands:

wizard
======
::

    $ spread wizard <project-path>

Start *spreads* in wizard mode. This will go through all of the steps outlined
below and store images and output files in *project-path*

configure
=========
::

    $ spread configure

This command sets up your cameras for shooting. Currently, this means nothing
more than assigning each of the cameras with a label 'left' or 'right', to
later help maintain the correct page order and apply the right rotation.
The UI will ask you to successively connect and turn on each of your cameras
and turn it off again when configuration has succeeded.
This command only has to be performed once for each set of cameras, as the
label is stored permanently on the cameras' internal memory.

shoot
=====
::

    $ spread shoot [--iso <int>] [--shutter <int/float/str>] [--zoom <int>]

This command will start a shooting workflow. As usual, you will be asked
to connect and turn on your cameras. The application will then set them up,
e.g. by switching them into record mode, disabling the flash and setting the
options listed below. You will then enter a loop, where both cameras will
trigger simultaneously when you press the **spacebar** or **b**. Press any
other key to finish scanning.

.. program:: spread-shoot

.. option:: --iso iso-level, -i iso-level

   Set the ISO sensitivity value used for shooting. The default value is
   **80**.

.. option:: --shutter shutter-speed, -s shutter-speed

   Set the shutter speed used for shooting. The value can be either an integer
   ("20"), a float ("12.7") or a fraction ("1/25").
   The default value is **1/25**.

.. option:: --zoom zoom-level, -z zoom-level

   Set the zoom level used for shooting. Accepts any integer starting from 0,
   although the application might throw an error if the level chosen exceeds
   your camera's supported range.

download
========
::

    $ spread download <project-directory

This will tell spreads to download all images from your cameras to the folder
*project-directory*. Images from both cameras will automatically be assembled
into a single directory, named **raw**. On success, the images will be removed
from the cameras.

.. program:: spread-download

.. option:: --keep, -k

   Do not remove the images from the cameras, once the download has been
   completed.

postprocess
===========
::

    $ spread postprocess [--jobs <int>] <project-directory>

Start the postprocessing workflog by calling each of the :ref:`postprocessing
plugins <postproc_plugs>` defined in the configuration one after the other (by
default: `autorotate <plug_autorotate>`, `scantailor <plug_scantailor>`,
`pdfbeads <plug_pdfbeads>`). All output files will be stored in
*project-directory*.

.. program:: spread-postprocess

.. option:: --jobs number-of-jobs, -j number-of-jobs

   Specify how many concurrent processes should be used for rotation and
   ScanTailor. By default, *spreads* will use as many as CPU cores are
   available.

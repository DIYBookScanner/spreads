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

This command sets up your devices for capturing. Currently, this means nothing
more than assigning each of the devices with a label 'left' or 'right', to
later help maintain the correct page order and apply the right rotation.
The UI will ask you to successively connect and turn on each of your devices
and turn it off again when configuration has succeeded.
This command only has to be performed once for each set of devices, as the
label is stored permanently on the devices' internal memory.

capture
=======
::

    $ spread capture

This command will start a capturing workflow. As usual, you will be asked
to connect and turn on your devices. The application will then set them up,
e.g. by switching them into record mode, disabling the flash and setting the
options listed below. You will then enter a loop, where both devices will
trigger simultaneously when you press the **b** key. Press any other key to
finish capturing. Consult the documentation of your device for available
options.

download
========
::

    $ spread download [OPTIONS] <project-directory

This will tell spreads to download all images from your devices to the folder
*project-directory*. Images from both devices will automatically be assembled
into a single directory, named **raw**. On success, the images will be removed
from the devices.

.. program:: spread-download

.. option:: --keep, -k

   Do not remove the images from the devices, once the download has been
   completed.


postprocess
===========
::

    $ spread postprocess [--jobs <int>] <project-directory>

Start the postprocessing workflow by calling each of the :ref:`postprocessing
plugins <postproc_plugs>` defined in the configuration one after the other (by
default: :ref:`autorotate <plug_autorotate>`, :ref:`scantailor <plug_scantailor>`).
The transformed images will be stored in *project-directory/done*.

.. program:: spread-postprocess

.. option:: --jobs number-of-jobs, -j number-of-jobs

   Specify how many concurrent processes should be used for rotation and
   ScanTailor. By default, *spreads* will use as many as CPU cores are
   available.

output
======
::

    $ spread output <project-directory>

Start the output workflow, calling each of the :ref:`output plugins
<output_plugs>` defined in the configuration (by
default: :ref:`pdfbeads <plug_pdfbeads>`). All output files will be stored in
*project-directory/out*.

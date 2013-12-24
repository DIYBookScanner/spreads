Command-Line Interface
**********************

**spread** is *spreads'* command-line interface.

It takes a *command* as its first argument::

    $ spread [--verbose] COMMAND [ARGS...]

All of *spreads'* functionality is accessible via the following commands:

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

This command lets you select a device driver and a set of plugins to activate.
It also allows you to set the target pages for your devices, in case you are
using two devices for capturing.

capture
=======
::

    $ spread capture [OPTIONS] <project-director>

This command will start a capturing workflow. Make sure that your devices are
turned on. After the application is done setting them up, you will enter a
loop, where all devices will trigger simultaneously (if not configured
otherwise, see below) when you press one of the capture keys (by default:
the **b** or **spacebar** key). Press *r* to discard the last capture and
retake it. Press *f* to finish the capture process.

.. program:: spread-capture

.. option:: --no-parallel-capture

   When using two devices, do not trigger them simultaneously but one after the
   other.

.. option:: --flip-target-pages

   When using two devices, flip the configured target pages, i.e. the camera
   configured to be *odd* will temporarily be the *even* device and vice versa.
   This can be useful when you are scanning e.g. East-Asian literature.


postprocess
===========
::

    $ spread postprocess [--jobs <int>] <project-directory>

Start the postprocessing workflow by calling each of the :ref:`postprocessing
plugins <postproc_plugs>` defined in the configuration one after the other.The
transformed images will be stored in *project-directory/done*.

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
<output_plugs>` defined in the configuration. All output files will be stored
in *project-directory/out*.

Command-Line Interface
**********************

**spread** is *spreads'* command-line interface.

It takes a *command* as its first argument::

    $ spread [--verbose] [--logfile=<path>] [--loglevel=<debug/info/warning/error>] COMMAND [ARGS...]

.. program:: spread

.. option:: --verbose

   Display debugging messages on the terminal

.. option:: --logfile [default: ~/.config/spreads/spreads.log]

   Write logging messages to this file.

.. option:: --loglevel [default: info]

   Verbosity of messages in logfile


All of *spreads'* functionality is accessible via the following commands:

wizard
======

configure
=========
::

    $ spread configure

This command lets you select a device driver and a set of plugins to activate.
It also allows you to set the target pages for your devices, in case you are
using two devices for capturing.

capture
=======


Extending *spreads*
*******************
.. _add_devices:

Adding support for new devices
==============================
To support new devices, you have to subclass :class:`DevicePlugin
<spreads.plugin.DevicePlugin>` in your module and add it as an entry point for
the ``spreadsplug.devices`` namespace to your package's ``setup.py``.  In it,
you override and implement the features supported by your device.  Take a look
at the `plugin for CHDK-based cameras`_ and the `relevant part of spreads'
setup.py`_ for a reference implementation.

Devices are assigned a :class:`DevicePlugin <spreads.plugin.DevicePlugin>`
implementation based on their USB device's properties. This means that you
can support a whole range of devices with a single :class:`DevicePlugin
<spreads.plugin.DevicePlugin>` implementation, if you know a set of
attributes that apply to all of them.

.. _plugin for CHDK-based cameras: https://github.com/jbaiter/spreads/blob/master/spreadsplug/chdkcamera.py
.. _relevant part of spreads' setup.py: https://github.com/jbaiter/spreads/blob/master/setup.py

.. _extend_commands:

Extending *spreads* built-in commands
=====================================
You can extend all of *spread's* built-in commands with your own code. To do,
you just have to inherit from the :class:`HookPlugin
<spreads.plugin.HookPlugin>` class and implement one or more of its hooks.
Furthermore, you have to add an entry point for that class in the
``spreadsplug.hooks`` namespace in your package's ``setup.py`` file.
For a list of available hooks and their options, refer to the
:doc:`API documentation <api>`. Example implementations can be found on
GitHub_

.. _GitHub: https://github.com/jbaiter/spreads/blob/master/spreadsplug

.. seealso:: module :py:mod:`spreads.plugin`, module :py:mod:`spreads.util`


Adding new commands
===================
You can also add entirely new commands to the application. Simply subclass
:class:`HookPlugin <spreads.plugin.HookPlugin>` again,
implement the ``add_command_parser`` method and add your new class as an
entry point to the ``spreadsplug.hooks`` namespace. Your plugin class will
most probably be a very few lines, telling the CLI parser its name, arguments
and pass a function that will do the main work.

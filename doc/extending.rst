Extending *spreads*
*******************
.. _add_devices:

Adding support for new devices
==============================
To support new devices, just subclass :class:`DevicePlugin
<spreads.plugin.DevicePlugin>` somewhere in the ``spreadsplug`` namespace and
override and implement the features supported by your device. Take a look at
the `plugin for CHDK-based cameras`_ for a reference implementation.

Devices are assigned a :class:`DevicePlugin <spreads.plugin.DevicePlugin>`
implementation based on their USB device's properties. This means that you
can support a whole range of devices with a single :class:`DevicePlugin
<spreads.plugin.DevicePlugin>` implementation, if you know a set of
attributes that apply to all of them.

.. _plugin for CHDK-based cameras: https://github.com/jbaiter/spreads/blob/master/spreadsplug/chdkcamera.py

.. _extend_commands:

Extending *spreads* functionality
=================================
You can extend all of *spread's* built-in commands with your own code. To do,
you just have to inherit from one the :class:`HookPlugin
<spreads.plugin.HookPlugin>` class and implement one or more of its hooks.
For a list of available hooks and their options, refer to the
:doc:`API documentation <api>`. Example implementations can be found on
GitHub_

.. _GitHub: https://github.com/jbaiter/spreads/blob/master/spreadsplug

.. seealso:: module :py:mod:`spreads.plugin`, module :py:mod:`spreads.util`

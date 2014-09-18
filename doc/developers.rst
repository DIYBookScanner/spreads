Extending *spreads*
*******************

.. _development_environment:

Setting up a development environment
====================================

The easiest way to work on spreads is to install it to an editable
virtual Python environment using the ``virtualenv`` tool and installing
spreads into it using ``pip`` with the
``-e`` option. This option allows the virtual environment to treat a
spreads repository checked out from git as a live installation.

For example, on a Debian-based system, assuming the git repository
for spreads is checked out to ``./spreads``::

  virtualenv spreadsenv
  cd spreadsenv
  source ./bin/activate
  # The following dependencies are not pulled in automatically by
  # setuptools
  pip install cffi
  pip install jpegtran-cffi
  pip install -e ../spreads

Other prerequisite packages you may require include:

  libffi-dev libjpeg8-dev libturbojpeg

.. _add_devices:

Adding support for new devices
==============================
To support new devices, you have to subclass :class:`DevicePlugin
<spreads.plugin.DevicePlugin>` in your module and add it as an entry point for
the ``spreadsplug.devices`` namespace to your package's ``setup.py``.  In it,
you override and implement the features supported by your device.  Take a look
at the `plugin for CHDK-based cameras`_ and the `relevant part of spreads'
setup.py`_ for a reference implementation.

Devices have to implement a
`yield_devices<spreads.plugin.DevicePlugin.yield_devices>` method that scans
the system for supported devices and returns fully instantiated device objects
for those.


.. _plugin for CHDK-based cameras: https://github.com/DIYBookScanner/spreads/blob/master/spreadsplug/dev/chdkcamera.py
.. _relevant part of spreads' setup.py: https://github.com/DIYBookScanner/spreads/blob/master/setup.py

.. _declaring_options:

Declaring available configuration options for plugins
=====================================================
Device drivers (as well as all plugins) can implement the
`configuration_templates<spreads.plugin.SpreadsPlugin.configuration_template>`
method that returns a dictionary of setting keys and
`PluginOption<spreads.plugin.PluginOption>` objects.  These options will be
visible across all supported interfaces and also be read from the configuration
file and command-line arguments.

.. _extend_commands:

Extending *spreads* built-in commands
=====================================
You can extend all of *spread's* built-in commands with your own code. To do,
you just have to inherit from the :class:`HookPlugin
<spreads.plugin.HookPlugin>` class and one of the available mixin classes (at
the moment these are `CaptureHooksMixin<spreads.plugin.CaptureHooksMixin>`,
`TriggerHooksMixin<spreads.plugin.TriggerHooksMixin>`,
`ProcessHookMixin<spreads.plugin.ProcessHookMixin>`,
`OutputHookMixin<spreads.plugin.OutputHookMixin>`). You then have to implement
each of the required methods for the mixins of your choice.

Furthermore, you have to add an entry point for that class in the
``spreadsplug.hooks`` namespace in your package's ``setup.py`` file.  For a
list of available hooks and their options, refer to the :doc:`API documentation
<api>`. Example implementations can be found on GitHub_

.. _GitHub: https://github.com/DIYBookScanner/spreads/blob/master/spreadsplug

.. seealso:: module :py:mod:`spreads.plugin`, module :py:mod:`spreads.util`

.. _add_commands:

Adding new commands
===================
You can also add entirely new commands to the application. Simply subclass
:class:`HookPlugin <spreads.plugin.HookPlugin>` and
`SubcommandHookMixin<spreads.plugin.SubcommandHookMixin>`, implement the
``add_command_parser`` classmethod and add your new class as an entry point to
the ``spreadsplug.hooks`` namespace. See the web_ and gui_ plugins for examples
of plugins that add custom subcommands.


.. _web: https://github.com/DIYBookScanner/spreads/blob/master/spreadsplug/web/__init__.py
.. _gui: https://github.com/DIYBookScanner/spreds/blob/master/spreadsplug/gui/__init__.py

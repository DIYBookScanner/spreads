Extending *spreads*
*******************
.. _add_cameras:

Adding support for new cameras
==============================
To support new cameras, just subclass :class:`BaseCamera
<spreads.plugin.BaseCamera>` somewhere in the ``spreadsplug`` namespace and
override and implement the features supported by your camera. Take a look at
the `plugin for the Canon A2200`_ for a reference implementation.

Cameras are assigned a :class:`BaseCamera <spreads.plugin.BaseCamera>`
implementation based on their USB device and vendor IDs. This means that you
can support a whole range of devices with a single :class:`BaseCamera
<spreads.plugin.BaseCamera>` implementation, if you know their respective IDs.

.. seealso:: module :py:mod:`spreads.util`
.. _plugin for the Canon A2200: https://github.com/jbaiter/spreads/blob/master/spreadsplug/a2200.py

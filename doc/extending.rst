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
you just have to inherit from one of the :class:`SpreadsPlugin
<spreads.plugin.SpreadsPlugin>` subclasses and implement one or more of their
abstract methods.  The following types of plugins are available:

*capture* plugin
--------------
See :class:`CapturePlugin <spreads.plugin.CapturePlugin>`.

You can hook into the **capture** command by implementing :meth:`prepare
<spreads.plugin.CapturePlugin.prepare>` (executed before the capture process
begins), :meth:`capture <spreads.plugin.CapturePlugin.capture>` (executed every
time both devices have captured an image) and :meth:`finish
<spreads.plugin.CapturePlugin.finish>` (executed once the capture workflow has
finished).

*download* plugin
-----------------
See :class:`DownloadPlugin <spreads.plugin.DownloadPlugin>`.

Do stuff with the images downloaded from the device by implementing
:meth:`download <spreads.plugin.DownloadPlugin.download>` (executed once all
files are downloaded) and :meth:`delete <spreads.plugin.DownloadPlugin.delete>`
(executed once all files are deleted). By convention, all
:class:`DownloadPlugin <spreads.plugin.DownloadPlugin>` implementations only
modify the downloaded images in a **lossless** way, this means that while
information may be added to them (e.g. setting new metadata fields, rotating
them while preserving image quality, etc), no lossy changes may occur. Use
:class:`FilterPlugin <spreads.plugin.FilterPlugin>` for these types of changes.

Example implementation: spreadsplug.combine_

.. _spreadsplug.combine: https://github.com/jbaiter/spreads/blob/master/spreadsplug/combine.py


*postprocess* plugin
--------------------
See :class:`FilterPlugin <spreads.plugin.FilterPlugin>`.

Most plugins will probably fall into this category. Implement the :meth:`process
<spreads.plugin.FilterPlugin.process>` method to deal with the downloaded
images in ``project-path/raw`` in any way you please, as long as you don't
overwrite them.

Example implementations:

- spreadsplug.scantailor_ (image postprocessing)
- spreadsplug.pdfbeans_ (output generation)

.. _spreadsplug.scantailor: https://github.com/jbaiter/spreads/blob/master/spreadsplug/scantailor.py
.. _spreadsplug.pdfbeans: https://github.com/jbaiter/spreads/blob/master/spreadsplug/pdfbeans.py

.. seealso:: module :py:mod:`spreads.plugin`, module :py:mod:`spreads.util`

Extending *spreads*
*******************
.. _add_cameras:

Adding support for new cameras
==============================
To support new cameras, just subclass :class:`CameraPlugin
<spreads.plugin.CameraPlugin>` somewhere in the ``spreadsplug`` namespace and
override and implement the features supported by your camera. Take a look at
the `plugin for the Canon A2200`_ for a reference implementation.

Cameras are assigned a :class:`CameraPlugin <spreads.plugin.CameraPlugin>`
implementation based on their USB device and vendor IDs. This means that you
can support a whole range of devices with a single :class:`CameraPlugin
<spreads.plugin.CameraPlugin>` implementation, if you know their respective IDs.

.. _plugin for the Canon A2200: https://github.com/jbaiter/spreads/blob/master/spreadsplug/a2200.py

.. _extend_commands:

Extending *spreads* functionality
=================================
You can extend all of *spread's* built-in commands with your own code. To do,
you just have to inherit from one of the :class:`SpreadsPlugin
<spreads.plugin.SpreadsPlugin>` subclasses and implement one or more of their
abstract methods.  The following types of plugins are available:

ShootPlugin
-----------
See :class:`ShootPlugin <spreads.plugin.ShootPlugin>`.

You can hook into the **shoot** command by implementing :meth:`snap` (executed
every time both cameras have captured an image) and :meth:`finish` (executed
once the shooting workflow has finished).

DownloadPlugin
--------------
See :class:`DownloadPlugin <spreads.plugin.DownloadPlugin>`.

Do stuff with the images downloaded from the camera by implementing
:meth:`download <spreads.plugins.DownloadPlugin.download>` (executed once all
files are downloaded) and :meth:`delete <spreads.plugin.DownloadPlugin.delete>`
(executed once all files are deleted). By convention, all
:class:`DownloadPlugin <spreads.plugin.DownloadPlugin>` implementations only
modify the downloaded images in a **lossless** way, this means that while
information may be added to them (e.g. setting new metadata fields, rotating
them while preserving image quality, etc), no lossy changes may occur. Use
:class:`FilterPlugin <spreads.plugin.FilterPlugin>` for these types of changes.

Example implementation: spreadsplug.combine_

.. _spreadsplug.combine: https://github.com/jbaiter/spreads/blob/master/spreadsplug/combine.py


FilterPlugin
------------
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

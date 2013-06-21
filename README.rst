.. image:: https://raw.github.com/jbaiter/spreads/master/doc/_static/logo.png

.. image:: https://secure.travis-ci.org/jbaiter/spreads.png
   :target: http://travis-ci.org/jbaiter/spreads 

Introduction
------------
*spreads* is a tool that aims to streamline your book scanning workflow.
It takes care of every step: Setting up your capturing devices, handling
the shooting process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments beforehand, or by inspecting the output and
applying your modifications.

*spreads* is meant to be fully customizable. This means, adding support for
plugins is made as painless as possible.  Support for plugins that can
either hook into the various commands or add new ones is on the agenda,
stay tuned!


Quickstart
----------
*spreads* can be easily installed from PyPi::

    $ pip install git+git://github.com/jbaiter/spreads.git@master

*spreads* offers an interactive wizard that guides you through the whole
process::

    $ spread wizard ~/my_scanning_project


Features
--------
The following features are supported:

* Configure the cameras for shooting (i.e. configure which camera is left,
  which is right)
* Shoot with both cameras **simultaneously**
* Download images from cameras and combine them into a single directory
* Create a ScanTailor project file that the user can either further edit
  or run automatically
* Interactive Wizard-Mode that handles the full workflow from image
  capturing to post-processing

The following features are on the agenda, but not implemented yet:

* Automatically dewarp the scanned images using ppmunwarp_
* Do color-correction using a `graycard and imagemagick`_

Requirements
------------
* Python 2.7
* The `clint library`_ (used for the console interface)
* The `pillow library`_ (used to obtain EXIF information and rotate images)
* The `pyusb library`_ (used to obtain information about attached cameras)
* Two cameras running CHDK (development was done using two Canon A2200s,
  no further cameras were tested, but should work in theory)
* A version of `ptpcam modified for CHDK`_ in /usr/bin
* gphoto2
* An up-to date version of ScanTailor-enhanced_

Documentation
-------------
More documentation is available on readthedocs_

.. _DIYBookScanner: http://diybookscanner.org
.. _ppmunwarp: http://diybookscanner.org/forum/viewtopic.php?f=19&t=2589&p=14281#p14281
.. _graycard and imagemagick: http://diybookscanner.org/forum/viewtopic.php?f=20&t=2848
.. _clint library: https://github.com/kennethreitz/clint
.. _pillow library: https://github.com/python-imaging/Pillow
.. _pyusb library: https://pypi.python.org/pypi/pyusb/1.0.0a3
.. _ptpcam modified for CHDK: http://forum.chdk-treff.de/download/file.php?id=1640
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _ISO: http://chdk.wikia.com/wiki/CHDK_scripting#set_sv96
.. _shutter: http://chdk.wikia.com/wiki/CHDK_scripting#set_tv96_direct
.. _readthedocs: http://spreads.readthedocs.org

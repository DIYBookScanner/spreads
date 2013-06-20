Installation
============
Prerequisites
-------------
* Two cameras running CHDK (development was done using two Canon A2200s,
  no further cameras were tested, but should work in theory)
* Python 2.7 with pip_ installed
* A version of `ptpcam modified for CHDK`_
* gphoto2
* An up-to date version of ScanTailor-enhanced_

.. _pip: http://www.pip-installer.org
.. _ptpcam modified for CHDK: http://forum.chdk-treff.de/download/file.php?id=1640
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/

Installing from PyPi
--------------------
This will grab the latest release and install all Python dependencies.

``$ pip install spreads``

Installing from GitHub
----------------------
Like from PyPi, only using the development version from GitHub (might break,
use with caution!)

``$ pip install git+git://github.com/jbaiter/spreads.git@master``


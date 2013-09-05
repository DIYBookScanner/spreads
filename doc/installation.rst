Installation
============
Prerequisites
-------------
* Python 2.7 with pip_ installed
* libusb with headers installed

The spreads gui requires the PySide python package. To compile PySide, you also want:
* cmake
* qt4-qmake
* libqt4-dev
* pyqt4-dev-tools
* libxslt1-dev

(These are Debian 7.1 package names. They may be slightly different on the platform of your choice.)

Optional requirements
---------------------
To use some of the included plugins, you might want to install the following
dependencies:

* An up-to date version of ScanTailor-enhanced_
* pdfbeads_
* djvubind_

.. _pip: http://www.pip-installer.org
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _pdfbeads: http://rubygems.org/gems/pdfbeads
.. _djvubind: http://code.google.com/p/djvubind/

Installing from PyPi
--------------------
This will grab the latest release and install all Python dependencies::

    $ pip install spreads

To install the optional gui, first install PySide::

    $ pip install PySide

Then add the gui plugin to the spreads configuration in ~/.config/spreads/config.yaml .

Installing from GitHub
----------------------
Like from PyPi, only using the development version from GitHub (might break,
use with caution!)::

    $ pip install git+git://github.com/jbaiter/spreads.git@master


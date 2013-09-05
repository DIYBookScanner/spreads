Installation
============
Prerequisites
-------------
* Python 2.7 with pip_ installed
* libusb with headers installed

Optional requirements
---------------------
To use some of the included plugins, you might want to install the following
dependencies:

* An up-to date version of ScanTailor-enhanced_
* pdfbeads_
* djvubind_
* PySide_ (available as `python-pyside` for Debian and Ubuntu)

.. _pip: http://www.pip-installer.org
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _pdfbeads: http://rubygems.org/gems/pdfbeads
.. _djvubind: http://code.google.com/p/djvubind/
.. _PySide: http://pyside.org

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


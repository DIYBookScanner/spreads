Installation
============

Prerequisites
-------------
* Python 2.7 with a recent version of pip_ installed

Installl requirements
---------------------
To use some of the included plugins, you might want to install the following
dependencies:

.. TODO: Check with spreadpi/spreadslive

* `chdkptp`_ to use cameras with the CHDK firmware (installed in
  `/usr/local/lib/chdkptp`)
* An up-to date version of ScanTailor-enhanced_
* pdfbeads_
* djvubind_
* PySide_ (available as `python-pyside` for Debian and Ubuntu)

.. _pip: http://www.pip-installer.org
.. _chdkptp: https://www.assembla.com/spaces/chdkptp/wiki
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _pdfbeads: http://rubygems.org/gems/pdfbeads
.. _djvubind: http://code.google.com/p/djvubind/
.. _PySide: http://pyside.org

Installing the core from PyPi
-----------------------------
This will grab the latest release and install all Python dependencies::

    $ sudo pip install spreads


Installing plugin dependencies
------------------------------
This will grab all Python dependencies for the selected plugins::

  $ sudo pip install spreads[chdkcamera,web,hidtrigger]

Adjust the list of plugins as needed.

Installing from GitHub
----------------------
Like from PyPi, only using the development version from GitHub (might break,
use with caution!)::

    $ sudo pip install git+git://github.com/DIYBookScanner/spreads.git@master


.. image:: https://raw.github.com/jbaiter/spreads/master/doc/_static/logo.png

.. image:: https://secure.travis-ci.org/jbaiter/spreads.png
   :target: http://travis-ci.org/jbaiter/spreads
   :alt: Build status

.. image:: https://coveralls.io/repos/jbaiter/spreads/badge.png?branch=master
   :target: https://coveralls.io/r/jbaiter/spreads?branch=master
   :alt: Coverage status

.. image:: https://pypip.in/v/spreads/badge.png
    :target: https://crate.io/packages/spreads/
    :alt: Latest PyPI version

*spreads* is a tool that aims to streamline your book scanning workflow.
It takes care of every step: Setting up your capturing devices, handling
the capturing process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments or changing the configuration beforehand, or by
inspecting the output and applying your modifications.

*spreads* is meant to be fully customizable. This means, `adding support for
new devices` is made as painless as possible. You can also hook into any of the
*spread* commands by implementing one of the available `plugin hooks` or even
`implement your own custom sub-commands`.


Quickstart
----------
First, make sure you have installed all of the requirements (see below).
Once this is done, *spreads* can be easily installed from PyPi::

    $ pip install spreads

To select your desired plugins and configure your devices::

    $ spread configure

*spreads* offers an interactive wizard that takes you from a physical book
to a digitized version in one single workflow with minimal user input::

    $ spread wizard ~/my_scanning_project


Features
--------
* Shoot with both cameras **simultaneously**, directly storing the images
  in a single directory on your computer in the right order.
* Automatically rotate the images and optionally adjust the white balance
  (if a gray card has been used during shooting).
* Create a ScanTailor project file that the user can customize as desired.
* Generate PDF and DJVU files with hidden text layers
* Interactive Wizard-Mode that handles the full workflow from image
  capturing to post-processing, either from the command-line or via graphical
  interface.

Requirements
------------
* Python 2.7 with pip_ installed
* libusb with headers installed
* exiftool_
* An up-to date version of ScanTailor-enhanced_

*Optional:*
* For the GUI: PySide_
* For CHDK cameras: An up-to-date version of chdkptp_
* For the ScanTailor plugin: ScanTailor-enhanced_
* For PDF output: pdfbeads_
* For DJVU output: djvubind_
* For OCR: tesseract_

Documentation
-------------
More documentation is available on readthedocs_

.. _adding support for new devices: http://spreads.readthedocs.org/en/latest/extending.html#adding-support-for-new-devices
.. _plugin hooks: http://spreads.readthedocs.org/en/latest/api.html#spreads-plugin
.. _implement your own custom sub-commands: http://spreads.readthedocs.org/en/latest/extending.html#adding-new-commands
.. _ppmunwarp: http://diybookscanner.org/forum/viewtopic.php?f=19&t=2589&p=14281#p14281
.. _readthedocs: http://spreads.readthedocs.org
.. _pip: http://www.pip-installer.org
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _pdfbeads: http://rubygems.org/gems/pdfbeads
.. _djvubind: http://code.google.com/p/djvubind/
.. _exiftool: http://www.sno.phy.queensu.ca/~phil/exiftool/
.. _chdkptp: https://www.assembla.com/spaces/chdkptp/wiki
.. _tesseract: http://code.google.com/p/tesseract-ocr/
.. _PySide: http://qt-project.org/wiki/PySide

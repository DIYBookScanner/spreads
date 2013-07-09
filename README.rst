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

.. image:: https://pypip.in/d/spreads/badge.png
    :target: https://crate.io/packages/spreads/
    :alt: Number of PyPI downloads

*spreads* is a tool that aims to streamline your book scanning workflow.
It takes care of every step: Setting up your capturing devices, handling
the capturing process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments or changing the configuration beforehand, or by
inspecting the output and applying your modifications.

*spreads* is meant to be fully customizable. This means, `adding support
for new devices`_ is made as painless as possible. You can also
hook into any of the *spread* commands by imlementing one of the available
`plugin classes`.


Quickstart
----------
*spreads* can be easily installed from PyPi::

    $ pip install spreads

*spreads* offers an interactive wizard that takes you from a physical book
to a digitized version in one single workflow with minimal user input::

    $ spread wizard ~/my_scanning_project


Features
--------
The following features are supported:

* Configure the cameras for shooting (i.e. configure which camera is left,
  which is right)
* Shoot with both cameras **simultaneously**
* Download images from cameras and combine them into a single directory
* Automatically rotate the images and optionally adjust the white balance
  (if a gray card has been used during shooting).
* Create a ScanTailor project file that the user can either further edit
  or run automatically
* Automaitcally generate PDF and DJVU output
* Interactive Wizard-Mode that handles the full workflow from image
  capturing to post-processing

The following features are on the agenda, but not implemented yet:

* Automatically dewarp the scanned images using ppmunwarp_

Requirements
------------
* Python 2.7 with pip_ installed
* libusb with headers installed
* An up-to date version of ScanTailor-enhanced_
* pdfbeads_
* djvubind_

Documentation
-------------
More documentation is available on readthedocs_

.. _adding support for new devices: http://spreads.readthedocs.org/en/latest/extending.html#adding-support-for-new-devices 
.. _plugin classes: http://spreads.readthedocs.org/en/latest/api.html#spreads-plugin 
.. _ppmunwarp: http://diybookscanner.org/forum/viewtopic.php?f=19&t=2589&p=14281#p14281
.. _readthedocs: http://spreads.readthedocs.org
.. _pip: http://www.pip-installer.org
.. _ScanTailor-enhanced: http://sourceforge.net/p/scantailor/code/ci/enhanced/tree/
.. _pdfbeads: http://rubygems.org/gems/pdfbeads
.. _djvubind: http://code.google.com/p/djvubind/

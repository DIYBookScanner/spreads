.. image:: https://raw.github.com/jbaiter/spreads/master/doc/_static/logo.png

.. image:: https://travis-ci.org/DIYBookScanner/spreads.svg?branch=master
    :target: https://travis-ci.org/DIYBookScanner/spreads
    :alt: Build status


*spreads* is a software suite for the digitization of printed material. Its
main focus is to integrate existing solutions for individual parts of the
scanning workflow into a cohesive package that is intuitive to use and easy to
extend.

At its core, it handles the communication with the imaging devices, the
post-processing of the captured material and its assembly into output formats
like PDF or ePub. On top of this base layer, we have built a variety of
interfaces that should fit into most use cases: A full-fledged and
mobile-friendly web interface that can be served from even the most
low-powered devices (like a Raspberry Pi), a graphical wizard for classical
desktop users and a bare-bones command-line interface for purists.

As for extensibility, we offer a plugin API that allows developers to hook into
almost every part of the architecture and extend the application according to
their needs. There are interfaces for developing a device driver to communicate
with new hardware and for writing new postprocessing or output plugins to take
advantage of a as of yet unsupported third-party software. There is even the
possibility to create a completely new user interface that is better suited for
specific environments.

Features
--------
* Support for cameras running CHDK as well as cameras supported by libgphoto2
  (experimental), with extensive configuration options.
* Cropping of the images during capture (only supported in web interface)
* Shoot with two devices simultaneously, directly storing the images in a
  single directory on your computer in the right order.
* Automatically rotate images
* Run captured images through ScanTailor (attended or unattended)
* Recognize text from the images through Tesseract OCR
* Generate PDF and DJVU files with hidden text layers
* Every project is stored in a directory on your computer and contains all the
  information that is needed in human-readable form, laid out according to the
  BagIt specification. This makes it easy to exchange projects between
  computers.

Interfaces
----------

Web
+++

.. image:: http://i.imgur.com/ujchTcq.png
   :alt: web interface

The interface with the most features. You have the choice between three
modes: *scanner*, *processor* and *full*. The first is ideal for slim
scanning workstations that just deal with the capturing of the images and
little more. From it, you can transfer your scans either to an USB stick or
another instance of spreads running in one of the other two modes (all from
your browser!), where they will be post-processed. It is currently the only
interface to support cropping during capture and on-the-fly changing of
settings during capture.

GUI
+++

.. image:: http://i.imgur.com/jmijJhY.png
   :alt: graphical interface

A graphical wizard that guides you through every step, from setting up the
devices to postprocessing the images

CLI
+++

.. image:: http://i.imgur.com/wwcaP96.png
   :alt: command-line interface

A text-only command-line interface that exposes each step as a subcommand.
Ideal for controlling a scanner over SSH and for command-line fetishists.


Getting Started
---------------
1. Install the system dependencies:

   * ``sudo apt-get install python2.7-dev python-pip build-essential pkg-config libffi-dev libturbojpeg-dev libmagickwand-dev python-cffi``

2. If you want to use a CHDK device:

   * ``sudo apt-get install liblua5.2-dev libusb-dev``
   * ``sudo pip install lupa --install-option="--no-luajit"``
   * ``sudo pip install chdkptp.py``

3. If you want to use a libgphoto2-supported device:

   * ``sudo apt-get install libgphoto2-dev``
   * ``sudo pip install gphoto2-cffi``

4. Install Python dependencies:

   * ``sudo pip install jpegtran-cffi Flask requests zipstream tornado Wand``
   * ``sudo pip install http://buildbot.diybookscanner.org/nightly/spreads-latest.tar.gz``

5. If you want to use the GUI:

   * ``sudo apt-get install python-pyside``

6. If you want to use djvu functionality:

   * ``sudo apt-get install djvubind``

6. Configure spreads and select the plugins you want to use:

   * ``spread configure``


Documentation
-------------

You can find the detailed manual for users and developers at
http://spreads.readthedocs.org

Please note that it is currently woefully incomplete and partially out of date.
If you want to help with it, please get in touch!

Getting Help
------------

- IRC: irc.freenode.net, #diybookscanner
- Forums: http://diybookscanner.org/forums
- Bugtracker: https://github.com/DIYBookScanner/spreads/issues


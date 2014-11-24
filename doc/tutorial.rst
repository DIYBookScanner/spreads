Command-Line Tutorial
=====================

.. _cli_tutorial:

This tutorial assumes that you are using a setup with two Canon A2200 cameras
that have the latest version of CHDK installed. The rest of the setup is up to
you, though development and testing has been performed with a build of the
`DIYBookScanner`_. Furthermore, the following instructions are tailored to an
up-to-date installation of a Debian GNU/Linux installation or one of its
derivatives (\*buntu, Linux Mint, etc.). You might have to adjust the commands for
other distributions. This tutorial will also use most of the included plugins,
so the dependencies are rather numerous, though you can adapt that, if you
want.

The described (and recommended) way to install *spreads* is inside of a
`virtualenv`_, not system-wide, though you can do so as well, if you like.

.. _DIYBookScanner: http://diybookscanner.org/forum/viewtopic.php?f=1&t=1192 
.. _virtualenv: http://docs.python-guide.org/en/latest/dev/virtualenvs/

Installation
------------
First, ensure that you have all the dependencies installed::

    $ sudo apt-get install python2.7 python2.7-dev python-virtualenv libusb-dev\
      libjpeg-dev libtiff-dev libqt4-core rubygems ruby-rmagick libmagickwand-dev\
      ruby-hpricot scantailor djvulibre-bin libffi-dev libjpeg8-dev
    $ sudo gem install pdfbeads
    $ wget http://djvubind.googlecode.com/files/djvubind_1.2.1.deb
    $ sudo dpkg -i djvubind_1.2.1.deb
    # Download the latest 'chdkptp' release from the website:
    # https://www.assembla.com/spaces/chdkptp/documents
    $ sudo unzip chdkptp-<version>-<platform>.zip -d /usr/local/lib/chdkptp
    $ virtualenv ~/.spreads
    $ source ~/.spreads/bin/activate
    $ pip install spreads
    $ pip install spreads[chdkcamera]
    $ pip install spreads[autorotate]


Configuration
-------------

Workflow
--------
To begin, we run *spreads* in the **wizard** mode, which will guide us through
the whole workflow::

    $ spread wizard ~/my_book

On startup, your cameras will simultaneously adjust their zoom levels and set
their focus.  Once this is done, the application will ask you to press one of
your configured *shooting keys* (default: **b** or **space**). If you do so,
both cameras will take a picture simultaneously, which is then transferred to
our computer and stored under the correct filename in the `raw` subdirectory of
our project directory. Should you notice that you made a mistake during the
last capture, you can press **r** to discard the last capture and retake it.
Now scan as many pages as you need, when you're done, press **f** to
quit the capturing process and continue to the next step.

Next, spreads will begin with the postprocessing of the captured images. If you
followed the instructions so far, it will first rotate the images, which,
depending on your CPU and the number of images might take a minute or two.
Afterwards, *spreads* will launch a **ScanTailor** process in the background,
that will generate a configuration file (stored under
`~/my_book/my_book.ScanTailor`). When it has finished, it will open the
ScanTailor GUI, so you can make your final adjustments to the configuration.
Save and close your project when you're finished. *spreads* will then split the
configuration file into as many files as your computer has CPU cores and
perform the final ScanTailor step on all of them in parallel.

Finally, once ScanTailor has completed generating the final version of your
images ( in the `done` folder), it will generate PDF and DJVU files from them,
which you will find under the `~/my_book` directory.

If you want to know more about any of the above steps and how you can configure
them, check out the  entries for the appropriate :doc:`appropriate plugins
<plugins>`.


.. _gui_tutorial:

GUI Wizard
==========

Enabling the GUI
----------------
Usage
-----

Webinterface
============

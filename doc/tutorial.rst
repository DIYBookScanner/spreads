Command-Line Tutorial
=====================

.. _cli_tutorial:

This tutorial assumes that you are using a setup with two Canon A2200 cameras
that have the latest version of CHDK installed. The rest of the setup is up to
you, though development and testing has been performed with a build of the
`DIYBookScanner`_. Furthermore, the following instructions are tailored to an
up-to-date installation of a Debian GNU/Linux installation or one of its
derivates (\*buntu, Linux Mint, etc). You might have to adjust the commands for
other distributions. This tutorial will also use all of the included plugins,
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
      libhpricot-ruby scantailor
    $ sudo gem install pdfbeads
    $ wget http://djvubind.googlecode.com/files/djvubind_1.2.1.deb
    $ sudo dpkg -i djvubind_1.2.1.deb
    $ virtualenv ~/.spreads
    $ source ~/.spreads/bin/activate
    $ pip install spreads


Configuration
-------------
To perform the initial configuration, launch the `configure` subcommand::

    $ spread configure

.. TODO: Add link to --flip-target-pages

You will be asked to select a device driver (choose **a2200**) and some plugins
(choose all except **gui**). At the end, you can set the target pages for each
of your cameras. This is neccesary, as the application has to:

* combine the images from both cameras to a single directory in the right order
* set the correct rotation for the captured images

To do both of these things automatically, the application needs to know if the
image is showing an odd or even page. Don't worry, you only have to perform this
step once, the orientation is stored on the camera's memory card (under
`A/OWN.TXT`). Should you later wish to briefly flip the target pages, you can
do so via a command-line flag.

.. note::
    If you are using a DIYBookScanner, the device for *odd* pages is the
    camera on the **left**, the one for *even* pages on the **right**.

Once you're done, you can find the configuration file in the `.config/spreads`
folder in your home directory.

.. seealso:: :doc:`Configuring <configuring>`


Workflow
--------
To begin, we run *spreads* in the **wizard** mode, which will guide us through
the whole workflow::

    $ spread wizard ~/my_book

Follow the instructions and press your book against the platen, to allow the
cameras to automatically adjust their focus. This will be the focus that is
used throughout the capturing process, so make sure that the distance between
the pages and the cameras does not change significantly after this step!  When
you are prepared, press a button (or your footpedal) and your cameras will
simultaneously adjust their zoom levels and set their focus.

Once this is done, the application will ask you to press one of your configured
*shooting keys* (default: **b** or **space**). If you do so, both cameras will
take a picture simultaneously, which is then transferred to our computer and
stored under the correct filename in the `raw` subdirectory of our project
directory. Now scan as many pages as you need, when you're done, press any
other key to quit the capturing process and continue to the next step.

Now spreads will begin with the postprocessing of the captured images. If you
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
To enable the GUI wizard, first make sure that you have an up-to date version
of PySide installed on your machine and linked to your virtual environment::

    $ sudo apt-get install python-pyside
    $ ln -s /usr/lib/python2.7/dist-packages/PySide ~/.spreads/lib/python2.7/site-packages/PySide

Then, just add ``gui`` to the ``plugins`` list in your configuration file
(``~/.config/spreads/config.yaml`` on Linux).

Usage
-----
.. TODO: Update!
On the first screen, you can adjust various settings for your scan. You have
to specify a project directory (1) before you can continue. The rest of the
settings depends on which plugins you have enabled. In the screenshot you can
see that we are using the ``scantailor`` and ``tesseract`` plugins.
The ``Device for even pages`` setting is used by the ``autorotate`` and
``combine`` plugins and corresponds to their ``--first-page`` and
``--rotate-inverse`` options (``True`` for ``Right``).

.. figure:: _static/wizard1.png

   Initial setup page

The next screen allows you to select the devices you want to capture with.
You have to select at least one of them to be able to continue. You can always
refresh the list by clicking on the appropriate button. Once you have clicked
on ``Next``, spreads will prepare your devices for capture (i.e. switching
into record mode and applying the appropriate settings, see the above tutorial
for more details).

.. figure:: _static/wizard2.png

   Device selection page


Now you are at the capturing stage. The GUI shows you a preview for each
camera, that you can refresh by clicking on the button above it. Beneath
the preview images, you can see a text box that will display any warnings
and errors that might occur during this step. To toggle a capture, press
the appropriate button or hit ``b`` or ``space``, just like in the CLI
interface.

.. figure:: _static/wizard3.png

   Capture page

.. figure:: _static/wizard4.png

   Capture page with warnings/errors.


Next, spreads will try to download all the images from your devices, combine
them to a single directory and delete them from the devices (that is, if you
have not checked the ``Keep files on devices`` box on the first page).
You can follow the progress in the text box. In the case that there was an
inequal amount of images on the devices, you will get a warning and have to
fix the issue manually. You can then retry the combination by clicking the
button in the warning dialogue.

.. TODO: Insert screenshot of download page

Now spreads will run all of your enabled postprocessing plugins in sequence.
Just like during the download step, you can see the progress and any
warnings and errors in the text box. Once the postprocessing plugins are done,
it will try to generate the various output files as well.

.. TODO: Insert screenshot of postprocess/output page

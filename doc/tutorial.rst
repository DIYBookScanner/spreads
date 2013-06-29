Tutorial
========
This tutorial assumes that you are using a setup with two Canon A2200 cameras
that have the latest version of CHDK installed. The rest of the setup is up to
you, though development and testing has been performed with a build of the
`DIYBookScanner Hackerspace build`_. Furthermore, the following instructions
are tailored to an up-to-date installation of a Debian GNU/Linux installation
or one of its derivates (\*buntu, Linux Mint, etc). You might have to adjust
the commands for other distributions. This tutorial will also use all of the
included plugins, so the dependencies are rather numerous, though you can
adapt that, if you want.

The described (and recommended) way to install *spreads* is inside of a
virtualenv, not system-wide, though you can do so as well, if you like.

Installation
------------
First, ensure that you have all the dependencies installed::

    $ sudo apt-get install python2.7 python2.7-dev python-virtualenv libusb-dev\
      libjpeg-dev libtiff-dev libqt4-core rubygems ruby-rmagick
    $ wget <scantailor-deb-url>
    $ sudo dpkg -i <scantailor-deb>
    $ sudo gem install pdfbeads
    $ wget http://djvubind.googlecode.com/files/djvubind_1.2.1.deb
    $ sudo dpkg -i djvubind_1.2.1.deb
    $ virtualenv ~/.spreads
    $ ~/.spreads/bin/activate


Configuration
-------------
Upon startup, *spreads* will write its configuration file to
`~/.config/spreads/config.yml`. The file is heavily annotated, so you should
have no problem adjusting it to your needs.

.. seealso:: :doc:`Configuring <configuring>`


Workflow
--------
To begin, we run *spreads* in the **wizard** mode, which will guide you through
the whole workflow in one command::

    $ spread wizard ~/my_book

The application will then ask you to connection both of your cameras in turn to
configure them for shooting. The reason for this is, that the images from the
cameras will most likely be have to rotated and combined during postprocessing,
and by specifying which camera takes care of the left and right side of the
book spread, this process can be done automatically. Don't worry, you only have
to perform this step once, the orientation is stored on the camera's memory
card (under `A/OWN.TXT`).

When you are done with this step, the shooting process begins! You will notice
that your cameras will simultaneously move their lenses and adjust their zoom
levels. In the background, the cameras will also, among other things, set their
sensitivity levels and their shutter speeds to the values specified in the
configuration.

Once this is done, the application will ask you to press one of your configured
*shooting keys* (default: **b** or **space***). If you do so, both cameras will
take a picture simultaneously and store it to their memory card. We will not
transfer the images onto the computer until the capturing step has been
completed, as not to slow down scanning speed. If you're done capturing the
desired pages of your book, press any other key to stop the capturing loop.

Now spreads will automatically download all of the images just captured from
the cameras to the `left` and `right` subdirectories of the project path (in
this case: `~/my_book/`). Then, it will automatically combine the images into a
new folder, `raw`, and rotate them according to their camera of origin.  This
all happens automatically in the background, so you will most likely only see
your CPU usage spike up for a few seconds (when rotating the images).
Afterwards, *spreads* will launch a **ScanTailor** process in the background,
that will generate a configuration file (stored under
`~/my_book/my_book.ScanTailor`).  When it has finished, it will open the
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


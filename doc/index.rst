.. spreads documentation master file, created by
   sphinx-quickstart on Wed Jun 19 08:48:23 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

spreads
=======
Introduction
------------
*spreads* is a tool that aims to streamline your book scanning workflow.
It takes care of every step: Setting up your capturing devices, handling
the shooting process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments beforehand, or by inspecting the output and
applying your modifications.

.. *spreads* is meant to be fully customizable. This means, adding support
   for new cameras is made as painless as possible and you can hook into
   the scanning process at multiple points and add your own functions
   via plugins. (see :doc:`Extending spreads <extending>`)

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

Installation
------------
From PyPi
+++++++++
This will grab the latest release and install all Python dependencies.

``$ pip install spreads``

From GitHub
+++++++++++
Like from PyPi, only using the development version from GitHub (might break,
use with caution!)

``$ pip install git+git://github.com/jbaiter/spreads.git@master``

Quickstart
----------
*spreads* offers an interactive wizard that guides you through the whole
process:

``$ spread wizard ~/my_scanning_project``

Refer to the :doc:`Command-Line Reference <commands>` if you want a more
in-depth explanation of what is happening.

.. 1. Connect your cameras to your computer (at the moment only Canon A2200 models
   with the custom CHDK firmware are supported, but you can
   :doc:`change that! <extending>`).
   Make sure that you have *gphoto2* and *ptpcam* installed.
.. 2. Run the following command in the shell of your choice and follow the
   instructions on the screen:
   
..   ``$ spread configure``

.. 3. Now you can begin shooting:

..    ``$ spread shoot``

..    When you're done, press any key besides the **spacebar** or **b**.

.. 4. Time to get those images to your computer!

..    ``$ spread download ~/scans/mybook``

.. 5. And now let's make those scans pretty :-)

..    ``$ spread postprocess ~/scans/mybook``

.. If you want to know more about any of the above commands, check out their
.. respective entries in the :doc:`command-line reference <commands>`.

More Topics
-----------

.. toctree::
   :maxdepth: 2

   commands
   extending


.. note::

    In case you're wondering about the choice of mascot, the figure depicted is
    a Benedictine monk in his congregation's traditional costume, sourced from
    a `series of etchings`_ the German artist `Wenceslaus Hollar`_ did in the
    17th century on the robes of various religious orders. The book he holds in
    his hand is no accident, but was carefully chosen by the artist: The
    Benedictines_ used to be among the most prolific `copiers of books`_ in the
    middle-ages, preserving Europe's written cultural heritage, book spread for
    book spread, in a time when a lot of it was in danger of perishing.
    *spreads* wants to help you do the same in the present day.  Furthermore,
    the Benedictines were (and still are) very active missionaries, going out
    into the world and spreading 'the word'. *spreads* wants you to do the same
    with your digitized books (within the boundaries of copyright law, of
    course).

    .. _series of etchings: http://commons.wikimedia.org/wiki/Category:Clothing_of_religious_orders_by_Wenzel_Hollar
    .. _Wenceslaus Hollar: http://en.wikipedia.org/wiki/Wenceslaus_Hollar
    .. _Benedictines: http://en.wikipedia.org/wiki/Order_of_Saint_Benedict
    .. _copiers of books: http://en.wikipedia.org/wiki/Scriptorium

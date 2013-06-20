.. spreads documentation master file, created by
   sphinx-quickstart on Wed Jun 19 08:48:23 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Home Page
=========
Introduction
------------
*spreads* is a tool that aims to streamline your book scanning workflow.
It takes care of every step: Setting up your capturing devices, handling
the shooting process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments beforehand, or by inspecting the output and
applying your modifications.

*spreads* is meant to be fully customizable. This means, :ref:`adding support
for new cameras <add_cameras>` is made as painless as possible.  Support for
plugins that can either hook into the various commands or add new ones is on
the agenda, stay tuned!


Quickstart
----------
*spreads* can be easily installed from PyPi::

    $ pip install spreads

*spreads* offers an interactive wizard that guides you through the whole
process::

    $ spread wizard ~/my_scanning_project

Refer to the :doc:`Command-Line Reference <commands>` if you want a more
in-depth explanation of what is happening.


More Documentation
------------------
.. toctree::
   :maxdepth: 2

   self
   installation
   tutorial
   commands
   extending
   api

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



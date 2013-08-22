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
the capturing process, downloading the images to your machine,
post-processing them and finally assembling a variety of output formats.

Along the way you can always fine-tune the auto-generated results either
by supplying arguments beforehand, or by inspecting the output and
applying your modifications.

*spreads* is meant to be fully customizable. This means, :ref:`adding support
for new devices <add_devices>` is made as painless as possible. You can also
hook into any of the *spread* commands by implementing one of the available
:ref:`workflow hooks <extend_commands>` in a plugin, and you can even add
completely new commands and/or user interfaces, if you want to.


Quickstart
----------
*spreads* can be easily installed from PyPi::

    $ pip install spreads

*spreads* offers an interactive wizard that takes you from a physical book
to a digitized version in one single workflow with minimal user input::

    $ spread wizard ~/my_scanning_project

If you are more comfortable working with a GUI, a graphical version of the
wizard is included as well::

    $ spread gui

Refer to the :doc:`Command-Line Reference <commands>` if you want to explore
further commands and options.


More Documentation
------------------
.. toctree::
   :maxdepth: 2

   self
   tutorial
   installation
   configuring
   commands
   plugins
   extending
   faq
   api
   changelog

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



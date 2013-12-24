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

For this, you can make use of one of the three available user interfaces:
A handy graphical wizard that walks you through the whole process, a
lightweight command-line wizard or you can control each of the workflow steps
individually through their respective commands.

*spreads* is meant to be fully customizable. This means, :ref:`adding support
for new devices <add_devices>` is made as painless as possible. You can also
hook into any of the *spread* commands by implementing one of the available
:ref:`workflow hooks <extend_commands>` in a plugin, and you can even add
completely new commands and/or user interfaces, if you want to.


Quickstart
----------
*spreads* can be easily installed from PyPi::

    $ pip install spreads

Before you can start scanning books, you will have to configure the application::

    $ spread configure

Here, you can select a device driver, your desired plugins and setup your
devices.

Once you're done, you can start either the command-line or the GUI wizard::

    $ spread wizard ~/my_scanning_project
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
    a `series of 17th century etchings`_ by the Bohemian artist `Wenceslaus
    Hollar`_, depicting the robes of various religious orders. The book he
    holds in his hand is no accident, but was likely delibaretely chosen by the
    artist: The Benedictines_ used to be among the most prolific `copiers of
    books`_ in the middle-ages, preserving Europe's written cultural heritage,
    book spread for book spread, in a time when a lot of it was in danger of
    perishing.  *spreads* wants to help you do the same in the present day.
    Furthermore, the Benedictines were (and still are) very active
    missionaries, going out into the world and spreading 'the word'. *spreads*
    wants you to do the same with your digitized books (within the boundaries
    of copyright law, of course).

    .. _series of 17th century etchings: http://commons.wikimedia.org/wiki/Category:Clothing_of_religious_orders_by_Wenzel_Hollar
    .. _Wenceslaus Hollar: http://en.wikipedia.org/wiki/Wenceslaus_Hollar
    .. _Benedictines: http://en.wikipedia.org/wiki/Order_of_Saint_Benedict
    .. _copiers of books: http://en.wikipedia.org/wiki/Scriptorium



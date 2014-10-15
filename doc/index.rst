.. toctree::
   :maxdepth: 2

   setup-other
   setup-spreadpi
   web
   gui
   cli
   faq
   drivers
   plugins
   contributing
   developers
   api
   changelog

About Spreads
=============

spreads is a software suite for the digitization of printed material. Its main
focus is to integrate existing solutions for individual parts of the scanning
workflow into a cohesive package that is intuitive to use and easy to extend.

At its core, it handles the communication with the imaging devices, the
post-processing of the captured material and its assembly into output formats
like PDF or ePub. On top of this base layer, we have built a variety of
interfaces that should fit into most use cases: A full-fledged and
mobile-friendly :doc:`web interface <web>` that works on even the most
low-powered devices (like a Raspberry Pi, through the spreadpi distribution), a
:doc:`graphical wizard <gui>` for classical desktop users and a bare-bones
:doc:`command-line interface <cli>` for purists.

As for extensibility, we offer a plugin API that allows developers to hook into
almost every part of the architecture and extend the application according to
their needs. There are :ref:`interfaces for developing a device driver
<add_devices>` to communicate with new hardware, for writing new postprocessing
or output plugins to take advantage of a as of yet unsupported third-party
software. There is even the possibility to :ref:`create a completely new user
interface <add_commands>` that is better suited for specific environments.

The spreads core is completely written in the Python programming language,
which is widespread, easy to read and to learn (and beautiful on top of that).
Individual plugins also contain parts written in JavaScript and Lua. Through
the web-plugin it also offers a :doc:`REST(-ish) API <web_api>` that can be
accessed with any programming language that has a HTTP library.

To get started with the software, we suggest you begin by reading the
Introductory Notes that lay out the general workflow of the application and
explain some of the terminology used across all interfaces. Then, if you want
to install and configure the software yourself, head over to the
:doc:`Installation and Setup guide <setup-other>`. If you are a user of the
spreadpi distribution, use the :doc:`spreadpi guide <setup-spreadpi>`.

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

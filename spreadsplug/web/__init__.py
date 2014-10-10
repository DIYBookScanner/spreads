# -*- coding: utf-8 -*-

# Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Plugin to provide a RESTful HTTP API and a single-page web application for
controlling the software.

The code for the plug in is split across the following server-side modules:

:py:mod:`spreadsplug.web.app`
    Contains the subcommand hook as well as the initialization code for the
    web application.

:py:mod:`spreadsplug.web.endpoints`
    WSGI endpoints that provide most parts of the RESTful interface,
    implemented with Flask.

:py:mod:`spreadsplug.web.handlers`
    Tornado HTTP handlers for long-polling and chunked downloading endpoints,
    as well as a WebSocket handler for sending out server-side events to all
    clients.

:py:mod:`spreadsplug.web.tasks`
    Implementations of long-running tasks that are performed in the background,
    across multiple request-response-cycles, through the Huey task queue.

:py:mod:`spreadsplug.web.discovery`
    Code for both advertising of postprocessing-servers via UDP multi-casting,
    as well as the auto-discovery of said servers from other instances.

:py:mod:`spreadsplug.web.util`
    Various utility classes and functions for the plugin.

:py:mod:`spreadsplug.web.winservice`
    Code for a simple Windows service that runs the application in the
    background and provides a small taskbar-icon to allow opening a browser
    and shutting down the appplication.

For the documentation of the client-side part, please refer to the following
document: TODO

"""

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

""" Core web application code. """

import logging
import logging.handlers
import os
import sys
from itertools import chain
from threading import Thread

from spreads.vendor.confit import ConfigError
from spreads.vendor.huey import SqliteHuey
from spreads.vendor.huey.consumer import Consumer
from flask import Flask
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.web import FallbackHandler, Application

import spreads.workflow
import spreads.plugin as plugin
from spreads.util import is_os
from spreads.config import OptionTemplate
from spreads.main import add_argument_from_template, should_show_argument

#: Global application object
app = Flask('spreadsplug.web', static_url_path='/static',
            static_folder='./client/build', template_folder='./client')

#: Global task queue object
# NOTE: This has to be imported before the other modules since they depend
#       on it. However, it cannot be instantiated since we don't yet know
#       where we're supposed to store the queue.
task_queue = None
import endpoints
import util
import handlers
app.json_encoder = util.CustomJSONEncoder
from discovery import DiscoveryListener

#: Global logger
logger = logging.getLogger('spreadsplug.web')

try:
    # Most reliable way to get IP address, requires third-party package with
    # C extension
    import netifaces

    def get_ip_address():
        """ Return the first external IPv4 address using the
            :py:mod:`netifaces` module.

        :returns:   The IP address or ``None`` if it could not be determined
        """
        try:
            iface = next(dev for dev in netifaces.interfaces()
                         if 'wlan' in dev or 'eth' in dev or
                         dev.startswith('br'))
        except StopIteration:
            return None
        addresses = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addresses:
            return addresses[netifaces.AF_INET][0]['addr']
except ImportError:
    # Solution with built-ins, not as reliable
    import socket

    def get_ip_address():
        """ Return the first external IPv4 address using the :py:mod:`socket`
            module from the standard library.

        :returns:   The IP address or ``None`` if it could not be determined
        """
        try:
            return next(
                ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                if not ip.startswith("127."))
        except (StopIteration, socket.gaierror):
            return None


class WebCommands(plugin.HookPlugin, plugin.SubcommandHooksMixin):
    """ Plugin instance that registers the subcommands for the web plugin. """
    __name__ = 'web'

    @classmethod
    def add_command_parser(cls, rootparser, config):
        """
        Add subcommand parsers to root parser.

        :param rootparser: The root parser to add the subcommands to.
        :type rootparser:  :py:class:`argparse.ArgumentParser`
        :param config:     The application configuration
        :type config:      :py:class:`spreads.config.Configuration`
        """
        cmdparser = rootparser.add_parser(
            'web', help="Start the web interface")
        cmdparser.set_defaults(subcommand=cls.run)

        if is_os('windows'):
            wincmdparser = rootparser.add_parser(
                'web-service', help="Start the web interface as a service."
            )
            wincmdparser.set_defaults(subcommand=cls.run_windows_service)

        for key, option in cls.configuration_template().iteritems():
            if not should_show_argument(option, config['plugins'].get()):
                continue
            try:
                add_argument_from_template('web', key, option, cmdparser,
                                           config['web'][key].get())
                if is_os('windows'):
                    add_argument_from_template('web', key, option,
                                               wincmdparser,
                                               config['web'][key].get())
            except TypeError:
                continue

    @classmethod
    def configuration_template(cls):
        return {
            'mode': OptionTemplate(
                value=["full", "scanner", "processor"],
                docstring="Mode to run server in",
                selectable=True),
            'debug': OptionTemplate(
                value=False,
                docstring="Run server in debugging mode",
                selectable=False),
            'project_dir': OptionTemplate(
                value=u"~/scans",
                docstring="Directory for project folders",
                selectable=False),
            'postprocessing_server': OptionTemplate(
                value=u"",  # Cannot be None because of type deduction in
                            # option parser
                docstring="Address of the postprocessing server",
                selectable=False),
            'standalone_device': OptionTemplate(
                value=False,
                docstring="Server runs on a standalone device dedicated to "
                          "scanning (e.g. 'spreadpi').",
                selectable=False),
            'port': OptionTemplate(
                value=5000,
                docstring="TCP-Port to listen on",
                selectable=False),
        }

    @staticmethod
    def run(config):
        """ Initialize the web application and run it. """
        app = WebApplication(config)
        app.run_server()

    @staticmethod
    def run_windows_service(config):
        """ Initialize the web application and run it in the background, while
            displaying a small system tray icon to interact with the it.
        """
        import webbrowser
        from winservice import SysTrayIcon

        app = WebApplication(config)
        server_thread = Thread(target=app.run_server)
        server_thread.start()

        def on_quit(systray):
            """ Callback that stops the application. """
            IOLoop.instance().stop()
            server_thread.join()

        listening_port = config['web']['port'].get(int)
        open_browser = (
            lambda x: webbrowser.open_new_tab("http://127.0.0.1:{0}"
                                              .format(listening_port)))
        menu_options = (('Open in browser', None, open_browser),)

        SysTrayIcon(
            icon=os.path.join(os.path.dirname(sys.argv[0]), 'spreads.ico'),
            hover_text="Spreads Web Service",
            menu_options=menu_options,
            on_quit=on_quit,
            default_menu_index=1,
            on_click=open_browser)


class WebApplication(object):
    """ Manages initialization, configuration and launch of the web app.

    :attr config:           Web plugin configuration
    :type config:           :py:class:`confit.ConfigView`
    :attr global_config:    Global application configuration
    :type global_config:    :py:class:`spreads.config.Configuration`
    :attr consumer:         Background task consumer
    :type consumer:         :py:class:`huey.consumer.Consumer`
    :attr application:      Tornado web application
    :type application:      :py:class:`tornado.web.Application`
    """
    def __init__(self, config):
        self.global_config = config
        self.config = config['web']
        mode = self.config['mode'].get()
        logger.debug("Starting scanning station server in \"{0}\" mode"
                     .format(mode))
        # Directory that workflows should be stored in
        project_dir = os.path.expanduser(self.config['project_dir'].get())
        if not os.path.exists(project_dir):
            os.mkdir(project_dir)

        self._debug = self.config['debug'].get(bool)

        # Expose some configuration to the WSGI app
        app.config['debug'] = self._debug
        app.config['mode'] = mode
        app.config['base_path'] = project_dir
        app.config['default_config'] = config
        app.config['standalone'] = self.config['standalone_device'].get()
        app.config['postprocessing_server'] = (
            self.config['postprocessing_server'].get() or None)
        if not self._debug:
            app.error_handler_spec[None][500] = (
                endpoints.handle_general_exception)

    def setup_task_queue(self):
        """ Configure task queue and consumer. """
        # Initialize huey task queue
        global task_queue
        db_location = self.global_config.cfg_path.parent / 'queue.db'
        task_queue = SqliteHuey(location=unicode(db_location))
        self.consumer = Consumer(task_queue)

    def setup_logging(self):
        """ Configure loggers. """
        # Add in-memory log handler
        memoryhandler = logging.handlers.BufferingHandler(1024*10)
        memoryhandler.setLevel(logging.DEBUG)
        logger.root.addHandler(memoryhandler)

        # Silence some rather annoying loggers
        logging.getLogger('huey.consumer').setLevel(logging.INFO)
        logging.getLogger('huey.consumer.ConsumerThread').setLevel(
            logging.INFO)
        logging.getLogger('bagit').setLevel(logging.ERROR)
        logging.getLogger('isbnlib.dev.webservice').setLevel(logging.ERROR)
        logging.getLogger('tornado.access').setLevel(logging.ERROR)

    def setup_signals(self):
        """ Connect signal handlers. """
        def get_signal_callback_http(signal):
            """ Create a signal callback that adds a signal as a
                :py:class:`util.Event` to the buffer in :py:mod:`handlers`.
            """
            def signal_callback(sender, **kwargs):
                event = util.Event(signal, sender, kwargs)
                handlers.event_buffer.new_events([event])
            return signal_callback

        def get_signal_callback_websockets(signal):
            """ Create a signal callback that sends out a signals as a
                :py:class:`util.Event` via the
                :py:class:`tornado.web.WebSocketHandler` in :py:mod:`handlers`.
            """
            def signal_callback(sender, **kwargs):
                handlers.WebSocketHandler.send_event(
                    util.Event(signal, sender, kwargs))
            return signal_callback

        # Register event handlers
        import tasks
        signals_ = chain(*(x.signals.values()
                           for x in (spreads.workflow, util.EventHandler,
                                     tasks, handlers)))

        for signal in signals_:
            signal.connect(get_signal_callback_http(signal), weak=False)
            signal.connect(get_signal_callback_websockets(signal), weak=False)

    def setup_tornado(self):
        """ Configure Tornado web application. """
        if self._debug:
            # Exposes Werkzeug's interactive debugger for WSGI endpoints.
            logger.info("Starting server in debugging mode")
            from werkzeug.debug import DebuggedApplication
            container = WSGIContainer(DebuggedApplication(app, evalex=True))
        else:
            container = WSGIContainer(app)
        self.application = Application([
            (r"/ws", handlers.WebSocketHandler),
            (r"/api/workflow/([0-9a-z-]+)/download/(.*)\.zip",
             handlers.ZipDownloadHandler,
             dict(base_path=app.config['base_path'])),
            (r"/api/workflow/([0-9a-z-]+)/download/(.*).\.tar",
             handlers.TarDownloadHandler,
             dict(base_path=app.config['base_path'])),
            (r"/api/workflow/upload",
             handlers.StreamingUploadHandler,
             dict(base_path=app.config['base_path'])),
            (r"/api/poll", handlers.EventLongPollingHandler),
            # Fall back to WSGI endpoints
            (r".*", FallbackHandler, dict(fallback=container))
        ], debug=self._debug)

    def display_ip(self):
        """ Display external IP address on device displays. """
        # Display the address of the web interface on the camera displays
        try:
            for cam in plugin.get_devices(self.global_config):
                cam.show_textbox(
                    "\n    You can now access the web interface at:"
                    "\n\n\n         http://{0}:{1}"
                    .format(self._ip_address, self._listening_port))
            self._display_callback.stop()
        except plugin.DeviceException:
            # Try again next time...
            return

    def run_server(self):
        """ Run the web application. """
        self.setup_logging()
        self.setup_task_queue()
        self.setup_signals()
        self.setup_tornado()

        self._listening_port = self.config['port'].get(int)

        self._ip_address = get_ip_address()
        try:
            device_driver = plugin.get_driver(self.global_config['driver']
                                              .get())
            should_display_ip = (app.config['standalone'] and
                                 self._ip_address and
                                 plugin.DeviceFeatures.CAN_DISPLAY_TEXT in
                                 device_driver.features)
        except ConfigError:
            if self.config['mode'] not in ('scanner', 'full'):
                should_display_ip = False
            raise ConfigError(
                "You need to specify a value for `driver`.\n"
                "Either run `spread [gui]configure` or edit the configuration "
                "file.")

        if should_display_ip:
            # Every 30 seconds, see if there are devices attached and display
            # IP address and port on them, then disable the callback
            self._display_callback = PeriodicCallback(
                self.display_ip, 30*10**3)
            # Run once immediately
            self.display_ip()

        # Start task consumer
        self.consumer.start()

        # Start discovery listener
        if app.config['mode'] in ('processor', 'full'):
            discovery_listener = DiscoveryListener(self._listening_port)
            discovery_listener.start()

        # Spin up WSGI server
        self.application.listen(self._listening_port)

        try:
            IOLoop.instance().start()
        finally:
            # Shut everything down that is still running in the background
            self.consumer.shutdown()
            if app.config['mode'] in ('processor', 'full'):
                discovery_listener.stop()

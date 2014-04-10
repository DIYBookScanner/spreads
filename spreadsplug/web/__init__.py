import logging
import logging.handlers
import os
import platform
from itertools import chain

from spreads.vendor.huey import SqliteHuey
from spreads.vendor.huey.consumer import Consumer
from spreads.vendor.pathlib import Path
from flask import Flask

import spreads.plugin as plugin
from spreads.config import OptionTemplate
from spreads.main import add_argument_from_template
from spreads.util import get_data_dir
from spreads.workflow import Workflow

app = Flask('spreadsplug.web', static_url_path='/static',
            static_folder='./client', template_folder='./client')
task_queue = None
import web
import persistence
import util
app.json_encoder = util.CustomJSONEncoder
from websockets import WebSocketServer


logger = logging.getLogger('spreadsplug.web')

try:
    # Most reliable way to get IP address, requires third-party package with
    # C extension
    import netifaces

    def get_ip_address():
        try:
            iface = next(dev for dev in netifaces.interfaces()
                         if 'wlan' in dev or 'eth' in dev
                         or dev.startswith('br'))
        except StopIteration:
            return None
        addresses = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addresses:
            return addresses[netifaces.AF_INET][0]['addr']
except ImportError:
    # Solution with built-ins, not as reliable
    import socket

    def get_ip_address():
        try:
            return next(
                ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                if not ip.startswith("127."))
        except StopIteration:
            return None


class WebCommands(plugin.HookPlugin, plugin.SubcommandHookMixin):
    @classmethod
    def add_command_parser(cls, rootparser):
        cmdparser = rootparser.add_parser(
            'web', help="Start the web interface")
        cmdparser.set_defaults(subcommand=run_server)
        for key, option in cls.configuration_template().iteritems():
            try:
                add_argument_from_template('web', key, option, cmdparser)
            except:
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
            'database': OptionTemplate(
                value=os.path.join(get_data_dir(), 'workflows.db'),
                docstring="Path to application database file",
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
                selectable=False)
        }


def setup_app(config):
    mode = config['web']['mode'].get()
    logger.debug("Starting scanning station server in \"{0}\" mode"
                 .format(mode))
    db_path = Path(config['web']['database'].get()).expanduser()
    project_dir = os.path.expanduser(config['web']['project_dir'].get())
    if not os.path.exists(project_dir):
        os.mkdir(project_dir)

    app.config['DEBUG'] = config['web']['debug'].get()
    app.config['mode'] = mode
    app.config['database'] = db_path
    app.config['base_path'] = project_dir
    app.config['default_config'] = config
    app.config['standalone'] = config['web']['standalone_device'].get()

    if mode == 'scanner':
        app.config['postproc_server'] = (
            config['web']['postprocessing_server'].get())


def setup_logging(config):
    # Add in-memory log handler
    memoryhandler = logging.handlers.BufferingHandler(1024*10)
    memoryhandler.setLevel(logging.DEBUG)
    logger.root.addHandler(memoryhandler)

    logging.getLogger('huey.consumer').setLevel(logging.INFO)
    (logging.getLogger('huey.consumer.ConsumerThread')
            .setLevel(logging.INFO))


def setup_signals(ws_server=None):
    def get_signal_callback_http(signal):
        def signal_callback(sender, **kwargs):
            web.event_queue.append(util.Event(signal, sender, kwargs))
        return signal_callback

    def get_signal_callback_websockets(signal):
        def signal_callback(sender, **kwargs):
            ws_server.send_event(util.Event(signal, sender, kwargs))
        return signal_callback

    # Register event handlers
    signals = chain(*(x.signals.values()
                      for x in (Workflow, util.EventHandler, web)))

    for signal in signals:
        signal.connect(get_signal_callback_http(signal), weak=False)
        if ws_server:
            signal.connect(get_signal_callback_websockets(signal), weak=False)


def run_server(config):
    ws_server = WebSocketServer(port=5001)
    setup_app(config)
    setup_logging(config)
    setup_signals(ws_server)

    # Initialize huey task queue
    global task_queue
    db_location = get_data_dir() / 'queue.db'
    task_queue = SqliteHuey(location=unicode(db_location))
    consumer = Consumer(task_queue)

    ip_address = get_ip_address()
    if (app.config['standalone'] and ip_address
            and config['driver'].get() == 'chdkcamera'):
        # Display the address of the web interface on the camera displays
        try:
            for cam in plugin.get_devices(config):
                cam.show_textbox(
                    "\n    You can now access the web interface at:"
                    "\n\n\n         http://{0}:5000".format(ip_address))
        except plugin.DeviceException:
            logger.warn("No devices could be found at startup.")

    # Start task consumer
    consumer.start()
    # Start websocket server
    ws_server.start()

    try:
        import waitress
        # NOTE: We spin up this obscene number of threads since we have
        #       some long-polling going on, which will always block
        #       one worker thread.
        waitress.serve(app, port=5000, threads=16)
    finally:
        consumer.shutdown()
        ws_server.stop()

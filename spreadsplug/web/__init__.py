import logging
import os

from flask import Flask
from flask.ext.compress import Compress
from spreads.plugin import HookPlugin, PluginOption, get_devices
from spreads.vendor.pathlib import Path
from spreads.util import add_argument_from_option

app = Flask('spreadsplug.web', static_url_path='', static_folder='./client',
            template_folder='./client')
import web
import persistence
from worker import ProcessingWorker

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
        return netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
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


class WebCommands(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        cmdparser = rootparser.add_parser(
            'web', help="Start the web interface")
        cmdparser.set_defaults(subcommand=run_server)
        for key, option in cls.configuration_template().iteritems():
            try:
                add_argument_from_option('web', key, option, cmdparser)
            except:
                continue

    @classmethod
    def configuration_template(cls):
        return {
            'mode': PluginOption(
                value=["full", "scanner", "processor"],
                docstring="Mode to run server in",
                selectable=True),
            'debug': PluginOption(
                value=False,
                docstring="Run server in debugging mode",
                selectable=False),
            'project_dir': PluginOption(
                value=u"~/scans",
                docstring="Directory for project folders",
                selectable=False),
            'database': PluginOption(
                value=u"~/.config/spreads/workflows.db",
                docstring="Path to application database file",
                selectable=False),
            'postprocessing_server': PluginOption(
                value=u"",  # Cannot be None because of type deduction in
                            # option parser
                docstring="Address of the postprocessing server",
                selectable=False),
            'standalone_device': PluginOption(
                value=False,
                docstring="Server runs on a standalone device dedicated to "
                          "scanning (e.g. 'spreadpi').",
                selectable=False)
        }


def setup_app(config):
    # Set rootlogger to INFO
    if config['loglevel'].get() not in ('debug', 'info'):
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.INFO)

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


def run_server(config):
    setup_app(config)
    if app.config['mode'] != 'scanner':
        worker = ProcessingWorker()
        worker.start()

    ip_address = get_ip_address()
    if (app.config['standalone'] and ip_address
            and config['driver'].get() in ['chdkcamera', 'a2200']):
        # Display the address of the web interface on the camera displays
        try:
            for cam in get_devices(config):
                cam.show_textbox(
                    "\n    You can now access the web interface at:"
                    "\n\n\n         http://{0}:5000".format(ip_address))
        except:
            logger.warn("No devices could be found at startup.")

    try:
        import waitress
        # Activate HTTP compression
        Compress(app)
        waitress.serve(app, port=5000)
    finally:
        if app.config['mode'] != 'scanner':
            worker.stop()
        if app.config['DEBUG']:
            logger.info("Waiting for remaining connections to close...")

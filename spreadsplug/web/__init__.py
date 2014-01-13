import logging
import os
import shutil
import tempfile

from flask import Flask
from spreads.plugin import HookPlugin, PluginOption
from spreads.vendor.pathlib import Path

app = Flask('spreadsplug.web', static_url_path='', static_folder='./client')
import web
import persistence
from worker import ProcessingWorker

logger = logging.getLogger('spreadsplug.web')


class WebCommands(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        cmdparser = rootparser.add_parser(
            'web', help="Start the web interface")
        cmdparser.set_defaults(subcommand=cls.run_server)
        cmdparser.add_argument(
            '--mode', '-m', dest="web.mode",
            choices=['scanner', 'processor', 'full'],
            default='full')

    @classmethod
    def configuration_template(cls):
        return {
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
        }

    @staticmethod
    def run_server(config):
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

        app.config['mode'] = mode
        app.config['database'] = db_path
        app.config['base_path'] = project_dir
        app.config['default_config'] = config

        # Temporary directory for thumbnails, archives, etc.
        app.config['temp_dir'] = tempfile.mkdtemp()

        if mode == 'scanner':
            app.config['postproc_server'] = (
                config['web']['postprocessing_server'].get())
        if mode != 'scanner':
            worker = ProcessingWorker()
            worker.start()
        try:
            # TODO: Use gunicorn as the WSGI container, launch via paster
            app.run(host="0.0.0.0", threaded=True)
        finally:
            shutil.rmtree(app.config['temp_dir'])
            if mode != 'scanner':
                worker.stop()
            logger.info("Waiting for remaining connections to close...")

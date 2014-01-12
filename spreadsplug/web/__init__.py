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
        scanparser = rootparser.add_parser(
            'web-scanner', help="Start the scanning station server")
        scanparser.set_defaults(subcommand=cls.run_scanner)
        procparser = rootparser.add_parser(
            'web-processor', help="Start the postprocessing server")
        procparser.set_defaults(subcommand=cls.run_processor)
        fullparser = rootparser.add_parser(
            'web-full', help="Start the full server")
        fullparser.set_defaults(subcommand=cls.run_full)

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
    def run_scanner(config):
        run_in_mode('scanner', config)

    @staticmethod
    def run_processor(config):
        run_in_mode('processor', config)

    @staticmethod
    def run_full(config):
        run_in_mode('full', config)


def run_in_mode(mode, config):
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
        app.config['postproc_server'] = (config['web']['postprocessing_server']
                                         .get())
    if mode != 'scanner':
        worker = ProcessingWorker()
        worker.start()
    try:
        # TODO: Use gunicorn as the WSGI container, launch via paster
        app.run(threaded=True)
    finally:
        shutil.rmtree(app.config['temp_dir'])
        if mode != 'scanner':
            worker.stop()
        logger.info("Waiting for remaining connections to close...")

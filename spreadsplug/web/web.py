import logging

from flask import Flask, send_file

from spreads.plugin import HookPlugin, PluginOption
from spreadsplug.web.scanapi import scan_api

logger = logging.getLogger('spreadsplug.web')
app = Flask('spreadsplug.web', static_url_path='', static_folder='')


class WebCommands(HookPlugin):
    @classmethod
    def add_command_parser(cls, rootparser):
        scanparser = rootparser.add_parser(
            'web-scanner', help="Start the scanning station server")
        scanparser.set_defaults(func=run_scan_mode)

    @classmethod
    def configuration_template(cls):
        return {'path': PluginOption(value=u"~/scans",
                                     docstring="Directory for project folders",
                                     selectable=False),
                }


def run_scan_mode(args):
    logger.debug("Starting scanning station server")
    app.register_blueprint(scan_api, url_prefix='/api')
    app.run(debug=True)


@app.route('/')
def index():
    return send_file("index.html")

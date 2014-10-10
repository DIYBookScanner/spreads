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

""" Flask/WSGI endpoints.

These comprise the majority of the RESTful HTTP API. The other parts can be
found in the :py:mod:`handlers` module.
"""

from __future__ import division

import functools
import itertools
import logging
import logging.handlers
import subprocess
import sys
import traceback
from isbnlib import is_isbn10, is_isbn13

import pkg_resources
import requests
from flask import (json, jsonify, request, send_file, render_template,
                   redirect, make_response, Response)
from werkzeug.contrib.cache import SimpleCache

import spreads.metadata
import spreads.plugin as plugin
from spreads.util import is_os, get_version, DeviceException
from spreads.workflow import Workflow, ValidationError

from spreadsplug.web.app import app
from discovery import discover_servers
from util import WorkflowConverter, get_thumbnail, scale_image, convert_image

if is_os('windows'):
    from util import find_stick_win as find_stick
else:
    from util import find_stick

logger = logging.getLogger('spreadsplug.web')

#: Simple dictionary-based cache for expensive calculations
cache = SimpleCache()

# Register custom workflow converter for URL routes
app.url_map.converters['workflow'] = WorkflowConverter


class ApiException(Exception):
    """ General API error that cleanly serializes to JSON.

    :attr message:      Error message
    :type message:      unicode
    :attr status_code:  HTTP status code of the error (default: 500)
    :type status_code:  int
    :attr payload:      Error payload
    :type payload:      dict or object implementing ``to_dict``.
    :attr error_type:   Error type identifier
    :type error_type:   unicode
    """
    def __init__(self, message, status_code=500, payload=None,
                 error_type='general'):
        super(ApiException, self).__init__(message)
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.error_type = error_type

    def to_dict(self):
        return {
            'type': self.error_type,
            'payload': self.payload,
            'message': self.message
        }


@app.errorhandler(ValidationError)
def handle_validationerror(error):
    """ Handler for :py:class:`spreads.workflow.ValidationError` errors.

    Invokes the :py:class:`ApiException` error handler with status code 400,
    the validation errors as the payload and ``validation`` as the error type.
    """
    return handle_apiexception(ApiException(
        "There was an issue with at least some of the supplied values.",
        400, error.errors, 'validation'))


@app.errorhandler(ApiException)
def handle_apiexception(error):
    """ Handler for :py:class:`ApiException` errors.

    Returns a HTTP response with the error's status code and serialized to
    JSON.

    :resheader Content-Type:    :mimetype:`application/json`
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code or 500
    return response


@app.errorhandler(Exception)
def handle_general_exception(error):
    """ Handler for general :py:class:`Exception` errors.

    Returns a HTTP response with status code 500 and the error serialized to
    JSON, including a full traceback.

    :resheader Content-Type:    :mimetype:`application/json`
    """
    logger.exception(error)
    exc_type, exc, trace = sys.exc_info()
    response = jsonify({
        'message': error.message,
        'type': exc_type.__name__ if exc_type is not None else None,
        'traceback': traceback.format_tb(trace)
    })
    response.status_code = 500
    return response


# =================== #
#  General endpoints  #
# =================== #
@app.route('/')
def index():
    """ Deliver static landing page that launches the client-side app. """
    default_config = cache.get('default-config')
    if default_config is None:
        default_config = app.config['default_config'].flatten()
        cache.set('default-config', default_config)
    templates = cache.get('plugin-templates')
    if templates is None:
        templates = _get_templates()
        cache.set('plugin-templates', templates)
    return render_template(
        "index.html",
        version=get_version(),
        debug=app.config['debug'],
        default_config=default_config,
        plugins=_list_plugins(),
        config_templates=templates,
        metaschema=spreads.metadata.Metadata.SCHEMA,
    )


@app.route('/api/log')
def get_logs():
    """ Get application log.

    :queryparam start:  Index of first message (default: `0`)
    :type start:        int
    :queryparam count:  Number of messages to return (default: `50`)
    :type start:        int
    :queryparam level:  Maximum log level to be included in messages
                        (default: `INFO`)
    :type level:        str, one of `DEBUG`, `INFO`, `WARNING` or `ERROR`

    :resheader Content-Type:    :mimetype:`application/json`
    :>json boolean total_num:   Total number of messages
    :>json array messages:      Requested messages
    """
    start = int(request.args.get('start', '0'))
    count = int(request.args.get('count', '50'))
    level = request.args.get('level', 'INFO')
    logbuffer = next(
        x for x in logging.getLogger().handlers
        if isinstance(x, logging.handlers.BufferingHandler)).buffer
    available_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if level.upper() not in available_levels:
        levels = available_levels[available_levels.index('INFO'):]
    else:
        levels = available_levels[available_levels.index(level.upper()):]
    msgs = [msg for msg in sorted(logbuffer, key=lambda x: x.relativeCreated,
                                  reverse=True)
            if msg.levelname in levels]
    return jsonify(total_num=len(msgs),
                   messages=msgs[start:start+count])


@app.route('/api/isbn')
def query_isbn():
    """ Search for ISBN records.

    :queryparam q:  Search query
    :type q:        str

    :resheader Content-Type: :mimetype:`application/json`
    :>json array results:   Matching ISBN records
    :status 200:            When the query was successful
    :status 400:            When no search query was supplied
    """
    query = request.args.get('q')
    if query:
        return jsonify(results=spreads.metadata.get_isbn_suggestions(query))
    else:
        raise ValidationError(q='Missing parameter')


@app.route('/api/isbn/<isbn>')
def get_isbn_info(isbn):
    """ Get metadata for a given ISBN number.

    :param isbn:    ISBN number to retrieve metadata for
    :type isbn:     str/unicode with valid ISBN-10 or ISBN-13, optionally
                    prefixed with `isbn:`

    :resheader Content-Type: :mimetype:`application/json`
    :status 200:    When the ISBN was valid and a match was found.
    :status 400:    When the ISBN was invalid or no match was found.
    """
    if isbn.lower().startswith('isbn:'):
        isbn = isbn[5:]
    is_isbn = is_isbn10(isbn) or is_isbn13(isbn)
    if not is_isbn:
        raise ValidationError(isbn='Not a valid ISBN.')
    match = spreads.metadata.get_isbn_metadata(isbn)
    if match:
        return jsonify(match)
    else:
        raise ValidationError(isbn='Could not find match for ISBN.')


# ==================================== #
#  Plugin and Configuration endpoints  #
# ==================================== #
def _list_plugins():
    """ Get a the names of all activated plugins grouped by type.

    :rtype: dict (key: unicode, value: list of unicode)
    """
    config = app.config['default_config']
    plugins = plugin.get_plugins(*config['plugins'].get())
    return {
        'capture': [name for name, cls in plugins.iteritems()
                    if issubclass(cls, plugin.CaptureHooksMixin)],
        'trigger': [name for name, cls in plugins.iteritems()
                    if issubclass(cls, plugin.TriggerHooksMixin)],
        'postprocessing': [name for name, cls in plugins.iteritems()
                           if issubclass(cls, plugin.ProcessHooksMixin)],
        'output': [name for name, cls in plugins.iteritems()
                   if issubclass(cls, plugin.OutputHooksMixin)]
    }


def _get_templates():
    """ For every activated plugin, get all option templates.

    :rtype: dict
    """
    plugins = _list_plugins()
    config = app.config['default_config']
    if app.config['mode'] == 'scanner':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in plugins['capture'] or
                     section in plugins['trigger'] or
                     section in ('core', 'device', 'web')}
    elif app.config['mode'] == 'processor':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in plugins['postprocessing']
                     or section in ('core', 'web')}
    elif app.config['mode'] == 'full':
        templates = {section: config.templates[section]
                     for section in config.templates
                     if section in itertools.chain(*plugins.values())
                     or section in ('core', 'device', 'web')}
    rv = dict()
    for plugname, options in templates.iteritems():
        if options is None:
            continue
        for key, option in options.iteritems():
            if option.selectable:
                value = [config[plugname][key].get()]
                value += [x for x in option.value if x not in value]
            else:
                value = config[plugname][key].get()
            if plugname not in rv:
                rv[plugname] = dict()
            rv[plugname][key] = dict(value=value,
                                     docstring=option.docstring,
                                     selectable=option.selectable,
                                     advanced=option.advanced,
                                     depends=option.depends)
    return rv


def restrict_to_modes(*modes):
    """ Decorator that checks if the application is running in one or more
        specific modes and raises an error if otherwise.

    Must be placed after the :py:func:`flask.Flask.route` decorator.

    :param modes:   One or more modes (e.g. `scanner`, `processor`, `full`)
    :raises:        :py:class:`ApiException` when not running in one of the
                    specified modes
    """
    def decorator(func):
        @functools.wraps(func)
        def view_func(*args, **kwargs):
            if app.config['mode'] not in modes:
                if len(modes) == 1:
                    raise ApiException(
                        "Action only possible when running in '{0}'  mode."
                        .format(modes[0]), 503)
                else:
                    raise ApiException(
                        "Action only possible when running {0} or {1} modes"
                        .format(", ".join(modes[:-1]), modes[-1]), 503)
            return func(*args, **kwargs)
        return view_func
    return decorator


@app.route('/api/plugins')
def get_available_plugins():
    """ Get names of available and activated postprocessing and output plugins.

    :resheader Content-Type:        :mimetype:`application/json`
    :>json array postprocessing:    List of postprocessing plugin names
    :>json array output:            List of output plugin names
    """
    exts = list(pkg_resources.iter_entry_points('spreadsplug.hooks'))
    activated = app.config['default_config']['plugins'].get()
    post_plugins = sorted(
        [ext.name for ext in exts if ext.name in activated
         and issubclass(ext.load(), plugin.ProcessHooksMixin)],
        key=lambda x: activated.index(x))
    return jsonify({
        'postprocessing': post_plugins,
        'output': [ext.name for ext in exts if ext.name in activated
                   and issubclass(ext.load(), plugin.OutputHooksMixin)]
    })


@app.route('/api/templates')
def template_endpoint():
    """ For every activated plugin, get all option templates.

    :resheader Content-Type:    :mimetype:`application/json`
    """
    return jsonify(_get_templates())


@app.route("/api/config", methods=['GET'])
def get_default_config():
    """ Get global default configuration.

    :resheader Content-Type:    :mimetype:`application/json`
    """
    default_config = cache.get('default-config')
    if default_config is None:
        default_config = app.config['default_config'].flatten()
        cache.set('default-config', default_config)
    return jsonify(default_config)


@app.route("/api/config", methods=['PUT'])
def update_default_config():
    """ Update global default configuration.

    If `core` or `web` settings were modified, the application will be
    restarted.

    :reqheader Content-Type: :mimetype:`application/json`

    :resheader Content-Type: :mimetype:`application/json`
    """
    # TODO: Validate input against option templates.
    current = app.config['default_config']
    new_values = json.loads(request.data)
    current._config.set(new_values)
    current.dump(current.cfg_path)
    if "core" in new_values or "web" in new_values:
        import tornado.autoreload as autoreload
        autoreload._reload()
    default_config = current.flatten()
    cache.set('default-config', default_config)
    return jsonify(default_config)


# ====================== #
#  Submission endpoints  #
# ====================== #
def _get_from_remote_server(server, endpoint):
    """ Make a `GET` request to an endpoint on a remote server and return its
        response content and status code.

    :param server:      Hostname of the server to make request on
    :param endpoint:    Route of the endpoint to make request on
    :returns:           Response content and status code
    """
    try:
        resp = requests.get('http://' + server + endpoint)
    except requests.ConnectionError:
        raise ValidationError(
            server="Could not reach server at supplied address.")
    return resp.content, resp.status_code


@app.route('/api/remote/discover')
@restrict_to_modes("scanner")
def discover_postprocessors():
    """ Get list of available postprocessing servers on network.

    :resheader Content-Type:    :mimetype:`application/json`
    :<json array servers:       List of available server addresses
    """
    servers = discover_servers()
    if app.config['postprocessing_server']:
        servers.append(app.config['postprocessing_server'].split(':'))
    return jsonify(servers=["{0}:{1}".format(*addr) for addr in servers])


@app.route('/api/remote/plugins')
@restrict_to_modes("scanner")
def get_remote_plugins():
    """ Get available plugin names from a remote server, grouped by type.

    Behaves exactly like :http:get:`/api/plugins`.

    :queryparam server:     Hostname of remote server

    :resheader Content-Type:    :mimetype:`application/json`
    """
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    data, status = _get_from_remote_server(request.args.get("server"),
                                           '/api/plugins')
    return make_response(data, status, {'Content-Type': 'application/json'})


@app.route('/api/remote/templates')
@restrict_to_modes("scanner")
def get_remote_templates():
    """ Get option templates for all available plugins from a remote server.

    Behaves exactly like :http:get:`/api/templates`.

    :queryparam server:     Hostname of remote server

    :resheader Content-Type:    :mimetype:`application/json`
    """
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    data, status = _get_from_remote_server(request.args.get("server"),
                                           '/api/templates')
    return make_response(data, status, {'Content-Type': 'application/json'})


@app.route('/api/remote/config')
@restrict_to_modes("scanner")
def get_remote_config():
    """ Get default configuration from a remote server.

    Behaves exactly like :http:get:`/api/config`.

    :queryparam server:     Hostname of remote server

    :resheader Content-Type:    :mimetype:`application/json`
    """
    # TODO: Shouldn't this the done via a CORS request on the client-side?
    data, status = _get_from_remote_server(request.args.get("server"),
                                           '/api/config')
    return make_response(data, status, {'Content-Type': 'application/json'})


# ================== #
#  Workflow-related  #
# ================== #
@app.route('/api/workflow', methods=['POST'])
def create_workflow():
    """ Create a new workflow.

    :reqheader Accept:      :mimetype:`application/json`
    :<json object config:   Configuration for new workflow
    :<json object metadata: Metadata for new workflow

    :resheader Content-Type:    :mimetype:`application/json`
    :status 200:                When everything was OK.
    :status 400:                When validation of configuration or metadata
                                failed.
    """
    data = json.loads(request.data)

    if data.get('config'):
        config = app.config['default_config'].with_overlay(
            data.get('config'))
    else:
        config = app.config['default_config']

    metadata = data.get('metadata', {})

    workflow = Workflow.create(location=app.config['base_path'],
                               config=config,
                               metadata=metadata)
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow', methods=['GET'])
def list_workflows():
    """ Return a list of all workflows.

    :resheader Content-Type:    :mimetype:`application/json`
    """
    workflows = Workflow.find_all(app.config['base_path'])
    return make_response(json.dumps(workflows.values()),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['GET'])
def get_workflow(workflow):
    """ Return a single workflow.

    :param workflow:    UUID or slug for a workflow
    :type workflow:     str

    :resheader Content-Type:    :mimetype:`application/json`
    """
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['PUT'])
def update_workflow(workflow):
    """ Update a single workflow.

    :param workflow:        UUID or slug for the workflow to be updated
    :type workflow:         str
    :<json object config:   Updated workflow configuration
    :<json object metadata: Updated workflow metadata

    :resheader Content-Type:    :mimetype:`application/json`
    :status 200:                When everything was OK.
    :status 400:                When validation of configuration or metadata
                                failed.
    """
    data = json.loads(request.data)
    config = data.get('config')
    metadata = data.get('metadata')
    # Update workflow configuration
    if config:
        workflow.update_configuration(config)
    # Update metadata
    if metadata:
        workflow.metadata = metadata
    # Persist to disk
    workflow.save()
    return make_response(json.dumps(workflow),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>', methods=['DELETE'])
def delete_workflow(workflow):
    """ Delete a single workflow from database and disk.

    :param workflow:    UUID or slug for the workflow to be updated
    :type workflow:     str

    :status 200:        When deletion was succesful
    """
    Workflow.remove(workflow)
    return jsonify({})


@app.route('/api/workflow/<workflow:workflow>/download', methods=['GET'])
def download_workflow(workflow):
    """ Redirect to download endpoint (see
        :py:class:`spreadsplug.web.handlers.ZipDownloadHandler` or
        :py:class:`spreadsplug.web.handlers.TarDownloadHandler`) with proper
        filename set.

    :param workflow:    UUID or slug for the workflow to download
    :type workflow:     str
    :queryparam fmt:    Archive format for download (`zip` or `tar`,
                        default: `tar`)

    :status 302:        Redirects to :http:get:`/api/workflow/\\
                        (str:workflow_id)/download/\\
                        (str:workflow_slug).(str:archive_extension)`
    """
    archive_format = request.args.get('fmt', 'tar')
    if archive_format not in ('zip', 'tar'):
        raise ValidationError(fmt='Must be zip or tar.')
    fname = "{0}.{1}".format(workflow.path.stem, archive_format)
    return redirect('/api/workflow/{0}/download/{1}'.format(
                    workflow.id, fname))


@app.route('/api/workflow/<workflow:workflow>/transfer', methods=['POST'])
def transfer_workflow(workflow):
    """ Enqueue workflow for transfer to an attached USB storage device.

    Requires that the `python-dbus` package is installed.

    Once the transfer was succesfully enqueued, watch for the
    :py:data:`spreadsplug.web.tasks.on_transfer_started` which is emitted
    when the transfer actually started and subsequently
    :py:data:`spreadsplug.web.tasks.on_transfer_progressed` and
    :py:data:`spreadsplug.web.tasks.on_transfer_completed`.

    :param workflow:    UUID or slug for the workflow to be transferred
    :type workflow:     str

    :status 200:        When the transfer was successfully enqueued.
    :status 500:        When the `python-dbus` package was not found.
    :status 503:        When no removable USB device could be found for
                        mounting.
    """
    try:
        stick = find_stick()
    except ImportError:
        raise ApiException(
            "The transfer feature requires that the `python-dbus` module is "
            "installed on the system.", error_type='transfer')
    if stick is None:
        raise ApiException(
            "Could not find a removable devices to transfer to."
            "If you have connected one, make sure that it is formatted with "
            "the FAT32 file system", 503, error_type='transfer')
    from tasks import transfer_to_stick
    transfer_to_stick(workflow.id, app.config['base_path'])
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/submit', methods=['POST'])
@restrict_to_modes("scanner")
def submit_workflow(workflow):
    """ Enqueue workflow for submission to a postprocessing server.

    It is possible to submit a configuration object that should be used
    on the remote end for the workflow.
    Optionally, it can be specified if postprocessing and output generation
    should immediately be enqueued on the remote server.

    Once the submission was succesfully enqueued, watch for the
    :py:data:`spreadsplug.web.tasks.on_submit_started` which is emitted
    when the submission actually started and subsequently
    :py:data:`spreadsplug.web.tasks.on_submit_progressed`,
    :py:data:`spreadsplug.web.tasks.on_submit_completed` and
    :py:data:`spreadsplug.web.tasks.on_submit_error`.

    :reqheader Accept:  :mimetype:`application/json`
    :param workflow:    UUID or slug for the workflow to be submitted
    :type workflow:     str
    :<json string server:           Address of server to submit to
    :<json object config:           Configuration to use for workflow on remote
                                    server.
    :<json boolean start_process:   Whether to enqueue workflow for
                                    post-processing on the remote server.
    :<json boolean start_output:    Whether to enqueue workflow for output
                                    generation on the remote server.

    :status 200:        When the transfer was successfully enqueued.
    :status 400:        When no postprocessing server was specified
    :status 500:        When the `python-dbus` package was not found.
    :status 503:        When no removable USB device could be found for
                        mounting.
    """
    data = json.loads(request.data)
    server = data.get('server')
    if not server:
        raise ValidationError(server="required")
    user_config = data.get('config', {})
    from tasks import upload_workflow
    upload_workflow(workflow.id, app.config['base_path'],
                    'http://{0}/api/workflow/upload'.format(server),
                    user_config,
                    start_process=data.get('start_process', False),
                    start_output=data.get('start_output', False))
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/output/<fname>')
def get_output_file(workflow, fname):
    """ Download an output file.

    :param workflow:    UUID or slug for the workflow to download from
    :type workflow:     str
    :param fname:       Filename of the output file to download
    :type fname:        str

    :status 200:        Everything OK.
    :status 404:        Workflow or filename not found
    """
    try:
        fpath = next(fp for fp in workflow.out_files if fp.name == fname)
    except StopIteration:
        raise ApiException("Could not find file with name '{0}' amongst "
                           "output files for workflow '{1}'"
                           .format(fname, workflow.id), 404)
    return send_file(unicode(fpath))


# =============== #
#  Page-related  #
# =============== #
def inject_page(func):
    """ Decorator that injects a :py:class:`spreads.workflow.Page` object
        into the decorated function as the first argument.

    Must be placed after the :py:func:`flask.Flask.route` decorator.
    """
    @functools.wraps(func)
    def view_func(*args, **kwargs):
        # If we can't obtain a page from the arguments, just pass directly
        # through to the original function
        if 'workflow' not in kwargs and 'number' not in kwargs:
            return func(*args, **kwargs)
        page = next((p for p in kwargs['workflow'].pages
                    if p.capture_num == kwargs['number']), None)
        if not page:
            raise ApiException(
                "Could not find page with capture number {1}"
                .format(kwargs['number']), 404)
        return func(*args, page=page, **kwargs)
    return view_func


def inject_page_image(func):
    """ Decorator that injects the path to a request image into the decorated
        function as the first argument, along with the
        :py:class:`spreads.workflow.Page` instance as the second argument.

    Must be placed after the :py:func:`flask.Flask.route` decorator.
    """
    @functools.wraps(func)
    def view_func(*args, **kwargs):
        if 'img_type' not in kwargs and 'plugname' not in kwargs:
            return func(*args, **kwargs)
        page = kwargs['page']
        img_type = kwargs['img_type']
        plugname = kwargs['plugname']
        if img_type not in ('raw', 'processed'):
            raise ValidationError(
                route=("Image type must be one of 'raw' or 'processed' "
                       "(was {0})".format(img_type)))
        exists = (plugname is None or plugname in page.processed_images)
        if not exists:
            raise ApiException("No processed file present for plugin '{0}'"
                               .format(plugname), 404)
        if img_type == 'raw':
            fpath = page.raw_image
        elif plugname is None:
            fpath = page.get_latest_processed(image_only=True)
        else:
            fpath = page.processed_images[plugname]
        return func(fpath, *args, **kwargs)
    return inject_page(view_func)


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>')
@inject_page
def get_single_page(page, workflow):
    """ Get a single page.

    :param workflow:    UUID or slug for a workflow
    :type workflow:     str
    :param number:      Capture number of requested page
    :type number:       int

    :resheader Content-Type:    :mimetype:`application/json`
    """
    return jsonify(dict(page=page))


@app.route('/api/workflow/<workflow:workflow>/page')
def get_all_pages(workflow):
    """ Get all pages for a workflow.

    :param workflow:    UUID or slug for a workflow
    :type workflow:     str

    :resheader Content-Type:    :mimetype:`application/json`
    """

    return make_response(json.dumps(workflow.pages),
                         200, {'Content-Type': 'application/json'})


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>',
           defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>'
           '/<plugname>')
@inject_page_image
def get_page_image(fpath, page, workflow, number, img_type, plugname):
    """ Get image for requested page.

    :param workflow:    UUID or slug for a workflow
    :type workflow:     str
    :param number:      Capture number of requested page
    :type number:       int
    :param img_type:    Type of image
    :type img_type:     str, one of `raw` or `processed`
    :param plugname:    Only applicable if `img_type` is `processed`,
                        selects the desired processed file by its key in the
                        :py:attr:`spreads.workflow.Workflow.processed_images`
                        dictionary.
    :type plugname:     str
    :queryparam width:  Optionally scale down image to the desired width
    :type width:        int
    :queryparam format: Optionally convert image to desired format.
                        If `browser` is specified, non-JPG or PNG images will
                        be converted to PNG.
    :type format:       str, either `browser` or a format string recognized
                        by Pillow: http://pillow.readthedocs.org/en/latest/\\
                                   handbook/image-file-formats.html

    :resheader Content-Type:    Depends on value of `format`, by default
                                the mime-type of the original image.
    """
    width = request.args.get('width', None)
    img_format = request.args.get('format', None)
    # FIXME: This clearly sucks, rework convert_image and scale_image to allow
    #        for it.
    if width is not None and img_format is not None:
        raise ApiException("Can not scale and convert at the same time.", 400)
    transformable = fpath.suffix.lower() in ('.jpg', '.jpeg', '.tif', '.tiff',
                                             '.png')
    if (width is not None or img_format is not None) and not transformable:
        raise ApiException("Can only scale/convert JPG, TIF or PNG files.",
                           400)
    if width:
        # Scale image if requested
        return scale_image(fpath, width=int(width))
    elif img_format:
        # Convert to target format
        if fpath.suffix.lower() not in ('.tif', '.tiff', '.jpg', '.jpeg'):
            img_format = 'png' if img_format == 'browser' else img_format
        return convert_image(fpath, img_format)
    else:
        # Send unmodified if no scaling/converting is requested
        return send_file(unicode(fpath))


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/'
           'thumb', defaults={'plugname': None})
@app.route('/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/'
           '<plugname>/thumb', methods=['GET'])
@inject_page_image
def get_page_image_thumb(fpath, page, workflow, number, img_type, plugname):
    """ Get thumbnail for a page image. """
    if fpath.suffix.lower() not in ('.jpg', '.jpeg', '.tif', '.tiff', '.png'):
        raise ApiException("Can not serve thumbnails for files with type {0}"
                           .format(fpath.suffix), 400)
    cache_key = "{0}.{1}.{2}".format(workflow.id, img_type, fpath.name)
    thumbnail = None
    if not request.args:
        thumbnail = cache.get(cache_key)
    if thumbnail is None:
        thumbnail = get_thumbnail(fpath)
        cache.set(cache_key, thumbnail)
    return Response(thumbnail, mimetype='image/jpeg')


@app.route('/api/workflow/<workflow:workflow>/page/<int:number>',
           methods=['DELETE'])
@inject_page
def delete_page(page, workflow):
    """ Remove a single page from a workflow. """
    workflow.remove_pages(page)
    return jsonify(dict(page=page))


@app.route(
    '/api/workflow/<workflow:workflow>/page/<int:number>/<img_type>/crop',
    methods=['POST'], defaults={'plugname': None})
@inject_page
def crop_workflow_image(page, workflow, img_type, plugname):
    """ Crop a page image in place. """
    # TODO: We have to update the checksum!
    if img_type != 'raw':
        raise ApiException("Can only crop raw images.", 400)
    left = int(request.args.get('left', 0))
    top = int(request.args.get('top', 0))
    width = int(request.args.get('width', 0)) or None
    height = int(request.args.get('height', 0)) or None
    workflow.crop_page(page, left, top, width, height, async=True)
    cache_key = "{0}.{1}.{2}".format(workflow.id, 'raw', page.raw_image.name)
    cache.delete(cache_key)
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/page', methods=['DELETE'])
def bulk_delete_pages(workflow):
    """ Delete multiple pages from a workflow with one request. """
    cap_nums = [p['capture_num'] for p in json.loads(request.data)['pages']]
    to_delete = [p for p in workflow.pages if p.capture_num in cap_nums]
    logger.debug("Bulk removing from workflow {0}: {1}".format(
        workflow.id, to_delete))
    workflow.remove_pages(*to_delete)
    return make_response(json.dumps(to_delete),
                         200, {'Content-Type': 'application/json'})


# ================= #
#  Capture-related  #
# ================= #
@app.route('/api/workflow/<workflow:workflow>/prepare_capture',
           methods=['POST'])
@restrict_to_modes("scanner", "full")
def prepare_capture(workflow):
    """ Prepare capture for the requested workflow. """
    # Check if any other workflow is active and finish, if neccessary
    logger.debug("Finishing previous workflows")
    wfitems = Workflow.find_all(app.config['base_path'], key='id').iteritems()
    for wfid, wf in wfitems:
        if wf.status['step'] == 'capture' and wf.status['prepared']:
            if wf is workflow and not request.args.get('reset'):
                return 'OK'
            wf.finish_capture()
    try:
        workflow.prepare_capture()
    except DeviceException as e:
        logger.error(e)
        raise ApiException("Could not prepare capture: {0}".format(e.message),
                           500, error_type='device')
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/capture', methods=['POST'])
@restrict_to_modes("scanner", "full")
def trigger_capture(workflow):
    """ Trigger a capture on the requested workflow.

    Optional parameter 'retake' specifies if the last shot is to be retaken.

    Returns the number of pages shot and a list of the pages captured by
    this call in JSON notation.
    """
    status = workflow.status
    if status['step'] != 'capture' or not status['prepared']:
        workflow.prepare_capture()
    try:
        workflow.capture(retake=('retake' in request.args))
    except IOError as e:
        logger.error(e)
        raise ApiException("Could not capture images: {0}"
                           .format(e.message), 500)
    except DeviceException as e:
        logger.error(e)
        raise ApiException("Could not capture image: {0}"
                           .format(e.message), 500, error_type='device')
    return jsonify({
        'pages_shot': len(workflow.pages),
        'pages': workflow.pages[-2:]
    })


@app.route('/api/workflow/<workflow:workflow>/finish_capture',
           methods=['POST'])
@restrict_to_modes("scanner", "full")
def finish_capture(workflow):
    """ Wrap up capture process on the requested workflow. """
    workflow.finish_capture()
    return 'OK'


# ======================= #
#  Postprocessing/Output  #
# ======================= #
@app.route('/api/workflow/<workflow:workflow>/process', methods=['POST'])
@restrict_to_modes("processor", "full")
def start_processing(workflow):
    """ Enqueue the specified workflow for postprocessing. """
    workflow._update_status(step='process', step_progress=None)
    from tasks import process_workflow
    process_workflow(workflow.id, app.config['base_path'])
    return 'OK'


@app.route('/api/workflow/<workflow:workflow>/output', methods=['POST'])
@restrict_to_modes("processor", "full")
def start_output_generation(workflow):
    """ Enqueue the specified workflow for output generation. """
    workflow._update_status(step='output', step_progress=None)
    from tasks import output_workflow
    output_workflow(workflow.id, app.config['base_path'])
    return 'OK'


# ================== #
#   System-related   #
# ================== #
def standalone_only(func):
    """ Decorator that must be placed after the :py:func:`flask.Flask.route`
        decorator and which verifies that the application is running in
        standalone mode.

    :raises:        :py:class:`ApiException` when not running in one of the
                    specified modes
    """
    @functools.wraps(func)
    def view_func(*args, **kwargs):
        if not app.config['standalone']:
            raise ApiException(
                "Only available when server is run in standalone mode", 503)
        return func(*args, **kwargs)
    return view_func


@app.route('/api/system/shutdown', methods=['POST'])
@standalone_only
def shutdown():
    """ Shut down device.

    Requires that the user running the application has permission to run
    `shutdown -h now` via `sudo`.
    Note that this endpoint will never send a response, clients should take
    this into account and set a low timeout value.
    """
    logger.info("Shutting device down")
    try:
        subprocess.check_call("/usr/bin/sudo -n /sbin/shutdown -h now".split())
    except (subprocess.CalledProcessError, OSError):
        raise ApiException("The user running the server process needs to have "
                           "permission to run /sbin/shutdown via sudo.", 500)
    return ''


@standalone_only
@app.route('/api/system/reboot', methods=['POST'])
def reboot():
    """ Reboot device.

    Requires that the user running the application has permission to run
    `shutdown -r now` via `sudo`.
    Note that this endpoint will never send a response, clients should take
    this into account and set a low timeout value.
    """
    try:
        subprocess.check_call("/usr/bin/sudo -n /sbin/shutdown -r now".split())
    except (subprocess.CalledProcessError, OSError):
        raise ApiException("The user running the server process needs to have "
                           "permission to run /sbin/shutdown via sudo.", 500)
    return ''


@app.route('/api/reset', methods=['POST'])
def reset():
    """ Restart the application.

    Note that this endpoint will never send a response, clients should take
    this into account and set a low timeout value.
    """
    import tornado.autoreload as autoreload
    autoreload._reload()


@app.route('/<path:path>')
def redirect_pushstate(path):
    """ Fallback route that redirects user to a client-side route.

    This makes it possible for users to bookmark a page and return to it later.
    """
    return redirect("/#{0}".format(path))

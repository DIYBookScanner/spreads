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
Configuration entities.
"""

from __future__ import unicode_literals

import copy
import logging

import spreads.vendor.confit as confit
from pathlib import Path

import spreads.util as util


class OptionTemplate(object):
    """ Definition of a configuration option.

    :attr value:      The default value for the option or a list of available
                      options if :py:attr`selectable` is True
    :type value:      object (or list/tuple when :py:attr:`selectable` is True)
    :attr docstring:  A string explaining the configuration option
    :type docstring:  unicode
    :attr selectable: Make the `OptionTemplate` a selectable, i.e. value
                      contains a list or tuple of acceptable values for this
                      option, with the first member being the default
                      selection.
    :type selectable: bool
    :attr advanced:   Whether the option is an advanced option
    :type advanced:   bool
    :attr depends:    Make option dependant of some other setting (if passed a
                      dict) or another plugin (if passed a string)
    :type depends:    dict/str
    """

    def __init__(self, value, docstring=None, selectable=False,
                 advanced=False, depends=None):
        self.value = value
        self.docstring = docstring
        self.selectable = selectable
        self.advanced = advanced
        self.depends = depends

    def __repr__(self):
        return ("OptionTemplate(value={0}, docstring={1}, selectable={2}"
                " advanced={3}, depends={4})"
                .format(repr(self.value), repr(self.docstring),
                        repr(self.selectable), repr(self.advanced),
                        repr(self.depends)))


# Configuration templates for the core
CORE_OPTIONS = {
    'verbose': OptionTemplate(value=False,
                              docstring="Enable verbose output"),
    'logfile': OptionTemplate(
        value=unicode(Path(util.get_data_dir())/'spreads.log'),
        docstring="Path to logfile"),
    'loglevel': OptionTemplate(value=['info', 'critical', 'error',
                                      'warning', 'debug'],
                               docstring="Logging level for logfile",
                               selectable=True),
    'capture_keys': OptionTemplate(value=[" ", "b"],
                                   docstring="Keys to trigger capture",
                                   selectable=False),
}


class Configuration(object):
    """ Entity managing configuration state.

    Uses :py:class:`confit.Configuration` underneath the hood and follows
    its 'overlay'-principle.
    Proxies :py:meth:`__getitem__` and :py:meth:`__setitem__` from it, so
    it can be used as a dict-like type.
    """
    def __init__(self, appname='spreads'):
        """ Create new instance and load default and current configuration.

        :param appname:     Application name, configuration will be loaded from
                            this name's default configuration directory
        """
        self._config = confit.Configuration(appname, __name__)
        self._config.read()
        if 'plugins' not in self._config.keys():
            self['plugins'] = []
        self.load_templates()
        self.load_defaults(overwrite=False)

    # ----------------------------------------- #
    # Proxied methods from confit.Configuration #
    def __getitem__(self, key):
        """ See :py:meth:`confit.ConfigView.__getitem__` """
        return self._config[key]

    def __setitem__(self, key, value):
        """ See :py:meth:`confit.ConfigView.__setitem__` """
        self._config[key] = value

    def keys(self):
        """ See :py:meth:`confit.ConfigView.keys` """
        return self._config.keys()

    def dump(self, filename=None, full=True, sections=None):
        """ See :py:meth:`confit.Configuration.dump` """
        return self._config.dump(unicode(filename), full, sections)

    def flatten(self):
        """ See :py:meth:`confit.Configuration.flatten` """
        return self._config.flatten()
    # ----------------------------------------- #

    def load_templates(self):
        """ Get all available configuration templates from the activated
        plugins.

        :returns:   Mapping from plugin name to template mappings.
        :rtype:     dict unicode -> (dict unicode ->
                    :py:class:`OptionTemplate`)
        """
        import spreads.plugin
        self.templates = {}
        self.templates['core'] = CORE_OPTIONS
        if 'driver' in self.keys():
            driver_name = self["driver"].get()
            self.templates['device'] = (
                spreads.plugin.get_driver(driver_name)
                       .configuration_template())
        plugins = spreads.plugin.get_plugins(*self["plugins"].get())
        for name, plugin in plugins.iteritems():
            tmpl = plugin.configuration_template()
            if tmpl:
                self.templates[name] = tmpl
        return self.templates

    @property
    def cfg_path(self):
        """ Path to YAML file of the user-specific configuration.

        :returns:   Path
        :rtype:     :py:class:`pathlib.Path`
        """
        return Path(self._config.config_dir()) / confit.CONFIG_FILENAME

    def with_overlay(self, overlay):
        """ Get a new configuration that overlays the provided configuration
        over the present configuration.

        :param overlay:   The configuration to be overlaid
        :type overlay:    :py:class:`confit.ConfigSource` or dict
        :return:          A new, merged configuration
        :rtype:           :py:class:`confit.Configuration`
        """
        new_config = copy.deepcopy(self._config)
        new_config.set(overlay)
        return new_config

    def as_view(self):
        """ Return the `Configuration` as a :py:class:`confit.ConfigView`
            instance.
        """
        return self._config

    def load_defaults(self, overwrite=True):
        """ Load default settings from option templates.

        :param overwrite:   Whether to overwrite already existing values
        """
        for section, template in self.templates.iteritems():
            self.set_from_template(section, template, overwrite)

    def set_from_template(self, section, template, overwrite=True):
        """ Set default options from templates.

        :param section:   Target section for settings
        :type section:    unicode
        :type template:   :py:class:`OptionTemplate`
        :param overwrite: Whether to overwrite already existing values
        """
        old_settings = self[section].flatten()
        settings = copy.deepcopy(old_settings)
        for key, option in template.iteritems():
            logging.info("Adding setting {0} from {1}"
                         .format(key, section))
            if not overwrite and key in old_settings:
                continue
            if option.selectable:
                settings[key] = option.value[0]
            else:
                settings[key] = option.value
        self[section].set(settings)

    def set_from_args(self, args):
        """ Apply settings from parsed command-line arguments.

        :param args:    Parsed command-line arguments
        :type args:     :py:class:`argparse.Namespace`
        """
        for argkey, value in args.__dict__.iteritems():
            skip = (value is None or
                    argkey == 'subcommand' or
                    argkey.startswith('_'))
            if skip:
                continue
            if '.' in argkey:
                section, key = argkey.split('.')
                self[section][key] = value
            else:
                self[argkey] = value

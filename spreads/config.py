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

import copy
import logging

import spreads.vendor.confit as confit
from spreads.vendor.pathlib import Path


class OptionTemplate(object):
    """ A configuration option.

    :attr value:      The default value for the option or a list of available
                      options if :attr selectable: is True
    :type value:      object (or list/tuple when :attr selectable: is True)
    :attr docstring:  A string explaining the configuration option
    :type docstring:  unicode
    :attr selectable: Make the OptionTemplate a selectable, i.e. value contains
                      a list or tuple of acceptable values for this option,
                      with the first member being the default selection.
    :type selectable: bool
    :attr advanced:   Whether the option is an advanced option
    :type advanced:   bool
    """

    def __init__(self, value, docstring=None, selectable=False,
                 advanced=False):
        self.value = value
        self.docstring = docstring
        self.selectable = selectable
        self.advanced = advanced

    def __repr__(self):
        return ("OptionTemplate(value={0}, docstring={1}, selectable={2}"
                " advanced={3})"
                .format(repr(self.value), repr(self.docstring),
                        repr(self.selectable), repr(self.advanced)))

class ConfigOption(OptionTemplate):
    def __init__(self, optiontemplate, config_value):
        self.config_value = config_value
        super(ConfigOption, self).__init__(optiontemplate.value,
                                           optiontemplate.docstring,
                                           optiontemplate.selectable,
                                           optiontemplate.advanced)

    def __repr__(self):
        return ("ConfigOption(config_value={0}, value={1}, docstring={2}, "
                "selectable={3}, advanced={4})"
                .format(repr(self.config_value), repr(self.value),
                        repr(self.docstring), repr(self.selectable),
                        repr(self.advanced)))

CORE_OPTIONS = {
    'verbose': OptionTemplate(value=False,
                              docstring="Enable verbose output"),
    'logfile': OptionTemplate(value="~/.config/spreads/spreads.log",
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
    def __init__(self, appname='spreads'):
        self._config = confit.Configuration(appname, __name__)
        self._config.read()
        if 'plugins' not in self._config.keys():
            self['plugins'] = []
        self.load_defaults(overwrite=False)

    # ----------------------------------------- #
    # Proxied methods from confit.Configuration #
    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def keys(self):
        return self._config.keys()

    def dump(self, filename=None, full=True, sections=None):
        return self._config.dump(unicode(filename), full, sections)

    def flatten(self):
        return self._config.flatten()
    # ----------------------------------------- #

    @property
    def templates(self):
        """ Get all available configuration templates.

        :rtype: dict

        """
        import spreads.plugin
        templates = {'core': CORE_OPTIONS}
        if 'driver' in self.keys():
            driver_name = self["driver"].get()
            templates['device'] = (spreads.plugin.get_driver(driver_name)
                                   .configuration_template())
        plugins = spreads.plugin.get_plugins(*self["plugins"].get())
        for name, plugin in plugins.iteritems():
            tmpl = plugin.configuration_template()
            if tmpl:
                templates[name] = tmpl
        return templates

    @property
    def initialized_templates(self):
        """ Gets all Templates as in templates but
            values are set to their config values

        :rtype dict
        """
        templates = {}
        for plugname, tmpl in self.templates.iteritems():
            name = plugname if plugname != "device" else "driver"
            plug = {}
            for key, view in tmpl.items():
                plug[key] = ConfigOption(view, self[plugname][key].get())
            templates[name] = plug
        return templates

    def cfg_path(self):
        return Path(self._config.config_dir()) / confit.CONFIG_FILENAME

    def with_overlay(self, overlay):
        """ Get a new configuration that overlays the provided configuration
        over the present configuration.

        :param overlay:   The configuration to be overlaid
        :type overlay:    confit.ConfigSource or dict
        :return:          A new, merged configuration
        :rtype:           confit.Configuration

        """
        new_config = copy.deepcopy(self._config)
        new_config.set(overlay)
        return new_config

    def as_view(self):
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
        :type template:   OptionTemplate
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
        """ Apply settings from parsed arguments.

        :type args:   argparse.Namespace

        """
        for argkey, value in args.__dict__.iteritems():
            skip = (value is None
                    or argkey == 'subcommand'
                    or argkey.startswith('_'))
            if skip:
                continue
            if '.' in argkey:
                section, key = argkey.split('.')
                self[section][key] = value
            else:
                self[argkey] = value

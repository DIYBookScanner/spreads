/** @jsx React.DOM */
/* global module, require */

/*
 * Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.

 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

(function() {
  'use strict';
  var React = require('react/addons'),
      _ = require('underscore'),
      merge = require('react/lib/merge'),
      foundation = require('./foundation.js'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      capitalize = require('../util.js').capitalize,
      row = foundation.row,
      column = foundation.column,
      fnButton = foundation.button,
      PluginOption, PluginWidget, PluginConfiguration, PluginSelector;


  /**
   * A single option component for the workflow configuration.
   *
   * @property {string} name        - Name of the option
   * @property {object} option
   * @property {function} bindFunc  - Function that establishes databinding
   * @property {string} [error]     - Error message for the option
   */
  PluginOption = React.createClass({
    render: function() {
      var name = this.props.name,
          option = this.props.option,
          /* If there is a docstring, use it as the label, otherwise use
           * the capitalized name */
          label =  <label htmlFor={name}>{option.docstring || capitalize(name)}</label>,
          input;
      if (option.selectable && _.isArray(option.value)) {
        /* Use a dropdown to represent selectable cfgValues */
        input = (
          <select id={name} multiple={false} value={this.props.value}
                  onChange={this.props.onChange}>
            {_.map(option.value, function(key) {
              return <option key={key} value={key}>{key}</option>;
            })}
          </select>
        );
      } else if (_.isArray(option.value)) {
        /* TODO: Currently we cannot deal with multi-valued options,
         *       change this! */
      } else if (typeof option.value === "boolean") {
        /* Use a checkbox to represent boolean cfgValues */
        input = <input id={name} type={"checkbox"} checked={this.props.value}
                       onChange={this.props.onChange} />;
      } else {
        /* Use a regular input to represent number or string cfgValues */
        var types = { "number": "number",
                      "string": "text" };

        input = <input id={name} type={types[typeof option.value]}
                       value={this.props.value} onChange={this.props.onChange} />;
      }
      var error = this.props.error && (<small className="error">{this.props.error}</small>);
      return (
        <row>
        {input &&
          <column>
            <row>
            {/* Labels are to the left of all inputs, except for checkboxes */}
            {input.props.type === 'checkbox' ?
              <column size={1}>{input}</column> : <column size={5}>{label}{error}</column>}
            {input.props.type === 'checkbox' ?
              <column size={11}>{label}</column> : <column size={7}>{input}{error}</column>}
            </row>
          </column>}
        </row>
      );
    }
  });

  /**
   * Collection of options for a single plugin
   *
   * @property {object} template       - Collection of templates for options
   * @property {string} plugin         - Name of the plugin
   * @property {function} bindFunc     - Function to call to establish databinding
   */
  PluginWidget = React.createClass({
    getHandleChange: function(key) {
      return function(e) {
        var cfgValues = _.clone(this.props.cfgValues);
        cfgValues[key] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        this.props.onChange(cfgValues);
      }.bind(this);
    },
    render: function() {
      var template = this.props.template,
          cfgValues = this.props.cfgValues;
      return (
        <div>
        {_.map(template, function(option, key) {
          if (!this.props.showAdvanced && option.advanced) {
              return;
          }
          return (<PluginOption name={key} option={option} key={key}
                                value={this.props.cfgValues[key]}
                                error={this.props.errors[key]}
                                onChange={this.getHandleChange(key)} />);
        }, this)}
        </div>
      );
    }
  });

  PluginSelector = React.createClass({
    render: function() {
      return (
      <row className="plugin-select">
        <column size={3}><label>Select {this.props.type} plugins</label></column>
        <column size={9} className="select-pane">
          {_.map(this.props.available, function(plugin) {
            var key = 'toggle-' + plugin;
            return (
              <row key={key}>
                <column>
                  <input id={key} type="checkbox"
                         checked={_.contains(this.props.enabled, plugin)}
                         onChange={function(e){
                            this.props.onChange(e.target.checked, plugin);
                         }.bind(this)} />
                  <label htmlFor={key}> {plugin} </label>
                </column>
              </row>);
          }.bind(this))}
        </column>
      </row>);
    }
  });

  /**
   * Container for all plugin configuration widgets.
   * Offers a dropdown to select a plugin to configure and displays
   * its configuration widget.
   *
   * @property {Workflow} workflow  - Workflow to set configuration for
   * @property {object} errors      - Validation errors
   *
   */
  PluginConfiguration = React.createClass({
    getInitialState: function() {
      return {
        /** Currently selected plugin */
        selectedSection: undefined,
        /** Validation errors (from components themselves */
        internalErrors: {},
        /** Only for initialization purposes, not intended to be kept in sync
         *  at all times. */
        config: this.props.config || {},
        advancedOpts: false
      };
    },
    handleChange: function(section, cfgValues) {
      var config = _.clone(this.state.config);
      config[section] = cfgValues;
      this.setState({config: config});
    },
    handlePluginToggle: function(enabled, pluginName) {
      var config = this.state.config;
      if (_.isUndefined(config.plugins)) config.plugins = [];
      if (enabled) {
        config.plugins.push(pluginName);
      } else {
        config.plugins = _.without(config.plugins, pluginName);
        delete config[pluginName];
      }
      this.setState({config: config});
    },
    toggleAdvanced: function(){
      this.setState({ advancedOpts: !this.state.advancedOpts });
    },
    getDefaultConfig: function(pluginName) {
      if (!_.has(this.props.templates, pluginName)) return;
      var template = this.props.templates[pluginName],
          config = {};
      _.each(template, function(option, key) {
        var value = window.config[pluginName][key] || option.value;
        config[key] = _.isArray(option.value) ? option.value[0] : option.value;
      });
      return config;
    },
    render: function() {
      var templates = this.props.templates,
          config = this.state.config,
          configSections = [],
          errors = merge(this.state.internalErrors, this.props.errors),
          availablePlugins = this.props.availablePlugins,
          selectedSection;

      if (_.isUndefined(availablePlugins) && !_.isUndefined(window.plugins)) {
        if (window.config.mode == 'scanner') {
          availablePlugins = _.omit(window.plugins, "postprocessing", "output");
        } else {
          availablePlugins = window.plugins;
        }
      } else if (_.isUndefined(availablePlugins)) {
        availablePlugins = {};
      }

      if (_.has(config, 'plugins')) {
        configSections = _.filter(config.plugins, function(plugin) {
            return !_.isEmpty(templates[plugin]);
        });
      }

      if (window.config.web.mode !== 'processor' &&
          !_.isEmpty(templates['device'])) {
          configSections.push('device');
      }

      /* If no section is explicitely selected, use the first one */
      selectedSection = this.state.selectedSection;
      if (!_.isEmpty(configSections) && !selectedSection) {
        selectedSection = configSections[0];
      }
      return (
        <row>
          <column size={['12', '10', '8']}>
            <fieldset className="config">
              <legend>Configuration</legend>
              {!_.isEmpty(availablePlugins.postprocessing) &&
                <PluginSelector type="postprocessing"
                                available={availablePlugins.postprocessing}
                                enabled={config.plugins}
                                onChange={this.handlePluginToggle} />}
              {!_.isEmpty(availablePlugins.output) &&
                <PluginSelector type="output"
                                available={availablePlugins.output}
                                enabled={config.plugins}
                                onChange={this.handlePluginToggle} />}
              <row style={{"border-top": "1px solid lightgray",
                           "padding-top": "1em"}}>
                <column>
                  <input id="check-advanced" type="checkbox" value={this.state.advancedOpts}
                          onChange={this.toggleAdvanced} />
                  <label htmlFor="check-advanced">Show advanced options</label>
                </column>
              </row>
              {!_.isEmpty(configSections) &&
              <row className="plugin-config">
                <column size={3}>
                {_.map(configSections, function(section) {
                  var active = selectedSection === section,
                      classes = React.addons.classSet({
                        "plugin-label": true,
                        active: active
                      });
                  return (
                    <row>
                      <column>
                        <a onClick={function() {
                          this.setState({selectedSection: section});
                        }.bind(this)}>
                          <label className={classes}>
                            {capitalize(section)}
                            {active && <i style={{"margin-right": "1rem",
                                                  "line-height": "inherit"}}
                                          className="fa fa-caret-right right" />}
                          </label>
                        </a>
                      </column>
                    </row>);
                }, this)}
                </column>
                <column size={9} className="config-pane">
                  <PluginWidget template={templates[selectedSection]}
                                showAdvanced={this.state.advancedOpts}
                                cfgValues={this.state.config[selectedSection] || this.getDefaultConfig(selectedSection)}
                                errors={errors[selectedSection] || {}}
                                onChange={function(cfgValues) {
                                  this.handleChange(selectedSection, cfgValues);
                                }.bind(this)} />
                </column>
              </row>}
            </fieldset>
          </column>
        </row>);
    }
  });

  module.exports = {
      PluginWidget: PluginWidget,
      PluginConfiguration: PluginConfiguration
  }


}());

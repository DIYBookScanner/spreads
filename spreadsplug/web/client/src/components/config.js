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
      PluginOption, PluginWidget, PluginConfiguration;


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
          bindFunc = this.props.bindFunc,
          /* If there is a docstring, use it as the label, otherwise use
           * the capitalized name */
          label =  <label htmlFor={name}>{option.docstring || capitalize(name)}</label>,
          input;
      if (option.selectable && _.isArray(option.value)) {
        /* Use a dropdown to represent selectable values */
        input = (
          <select id={name} multiple={false} valueLink={bindFunc(name)}>
            {_.map(option.value, function(key) {
              return <option key={key} value={key}>{key}</option>;
            })}
          </select>
        );
      } else if (_.isArray(option.value)) {
        /* TODO: Currently we cannot deal with multi-valued options,
         *       change this! */
        input = <em>oops</em>;
      } else if (typeof option.value === "boolean") {
        /* Use a checkbox to represent boolean values */
        input = <input id={name} type={"checkbox"} checkedLink={bindFunc(name)} />;
      } else {
        /* Use a regular input to represent number or string values */
        var types = { "number": "number",
                      "string": "text" };

        input = <input id={name} type={types[typeof option.value]} valueLink={bindFunc(name)} />;
      }
      return (
        <row>
          <column size='12'>
            {/* Labels are to the left of all inputs, except for checkboxes */}
            {input.props.type === 'checkbox' ? input : label}
            {input.props.type === 'checkbox' ? label : input}
            {/* Display error, if it is defined */}
            {this.props.error && <small className="error">{this.props.error}</small>}
          </column>
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
    render: function() {
      var template = this.props.template;
      return (
        <row>
          <column size='12'>
            <row>
              <column size='12'>
                <h3>{this.props.plugin}</h3>
              </column>
            </row>
            {_.map(template, function(option, key) {
              var path = 'config.' + this.props.plugin + '.' + key;
              if (!this.props.showAdvanced && option.advanced) {
                  return;
              }
              return (<PluginOption name={key} option={option} key={key}
                                    bindFunc={this.props.bindFunc}
                                    error={this.props.errors[path]} />);
            }, this)}
          </column>
        </row>
      );
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
    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin],

    /** Activates databinding for `workflow` model property. */
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {
        /** Currently selected plugin */
        selectedSection: undefined
      };
    },
    /**
     * Change selected plugin
     *
     * @param {React.event} event - Event that triggered the method call
     */
    handleSelect: function(event) {
      this.setState({selectedSection: event.target.value});
    },
    handlePluginToggle: function(enabled, pluginName) {
      var config = this.props.workflow.get('config');
      if (enabled) {
        config.plugins.push(pluginName);
        config[pluginName] = this.loadDefaultConfig(pluginName);
      } else {
        config.plugins = _.without(config.plugins, pluginName);
        delete config[pluginName];
      }
      this.props.workflow.set('config', config);
      this.forceUpdate();
    },
    toggleAdvanced: function(){
      this.setState({ advancedOpts: !this.state.advancedOpts });
      this.forceUpdate();
    },
    loadDefaultConfig: function(pluginName) {
      if (!_.has(this.props.templates, pluginName)) return;
      var template = this.props.templates[pluginName],
          config = {};
      _.each(template, function(option, key) {
        config[key] = option.value;
      });
    },
    render: function() {
      var templates = this.props.templates,
          workflow = this.props.workflow,
          configSections = [],
          selectedSection;

      if (this.props.workflow.get('config')) {
          configSections = _.filter(
            this.props.workflow.get('config').plugins, function(plugin) {
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
        <div>
          {this.props.availablePlugins &&
          <row>
            <column size={[12,9]}>
              {_.map(this.props.availablePlugins.postprocessing, function(plugin) {
                var key = 'toggle-' + plugin;
                return (
                  <div key={key}>
                    <input id={key} type="checkbox"
                           checked={_.contains(workflow.get('config').plugins, plugin)}
                           onChange={function(e){this.handlePluginToggle(e.target.checked, plugin);}.bind(this)} />
                    <label htmlFor={key}> {plugin} </label>
                  </div>
                );
              }.bind(this))}
            </column>
          </row>}
          {this.props.availablePlugins &&
          <row>
            <column size={[12,9]}>
              {_.map(this.props.availablePlugins.output, function(plugin) {
                var key = 'toggle-' + plugin;
                return (
                  <div key={key}>
                    <input id={key} type="checkbox"
                           checked={_.contains(workflow.get('config').plugins, plugin)}
                           onChange={function(e) {this.handlePluginToggle(e.target.checked, plugin)}.bind(this)}/>
                    <label htmlFor={key}>{plugin}</label>
                  </div>
                );
              }.bind(this))}
            </column>
          </row>}
          {!_.isEmpty(configSections) &&
          <row>
            <column size='12'>
              <label>Configure plugin</label>
              <select onChange={this.handleSelect}>
                {configSections.map(function(section) {
                  return <option key={section} value={section}>{capitalize(section)}</option>;
                })}
              </select>
              <input id="check-advanced" type="checkbox" value={this.state.advancedOpts}
                      onChange={this.toggleAdvanced} />
              <label htmlFor="check-advanced">Show advanced options</label>
              {/* NOTE: This is kind of nasty.... We can't use _'s 'partial',
                        since we want to provide the second argument and leave
                        the first one to the caller. */}
              <PluginWidget plugin={selectedSection}
                            template={templates[selectedSection]}
                            showAdvanced={this.state.advancedOpts}
                            bindFunc={function(key) {
                              return this.bindTo(
                                this.props.workflow,
                                'config.' + selectedSection + '.' + key);
                            }.bind(this)}
                            errors={this.props.errors}/>
            </column>
          </row>}
        </div>
      );
    }
  });

  module.exports = {
      PluginWidget: PluginWidget,
      PluginConfiguration: PluginConfiguration
  }


}());

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
      row = foundation.row,
      column = foundation.column,
      fnButton = foundation.button,
      PluginOption, PluginWidget, PluginConfiguration;

  /**
   * Some helper mixins for underscore that we're going to need
   *
   * @mixin
   */
  _.mixin({
    /**
     * Convert the first letter of a given string to uppercase.
     *
     * @param {string} string
     */
    capitalize: function(string) {
        return string.charAt(0).toUpperCase() + string.substring(1).toLowerCase();
      }
  });

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
          label =  <label htmlFor={name}>{option.docstring || _.capitalize(name)}</label>,
          input;
      if (option.selectable && _.isArray(option.value)) {
        /* Use a dropdown to represent selectable values */
        input = (
          <select id={name} multiple={false} valueLink={bindFunc(name)}>
            {_.map(option.value, function(key) {
              return <option value={key}>{key}</option>;
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
        selectedPlugin: undefined
      };
    },
    /**
     * Change selected plugin
     *
     * @param {React.event} event - Event that triggered the method call
     */
    handleSelect: function(event) {
      this.setState({selectedPlugin: event.target.value});
    },
    toggleAdvanced: function(){
      this.setState({ advancedOpts: !this.state.advancedOpts });
      this.forceUpdate();
    },
    render: function() {
      var templates = window.pluginTemplates,
          /* If no plugin is explicitely selected, use the first one */
          selectedPlugin = this.state.selectedPlugin || _.keys(templates)[0];
      /* Don't display anything if there are no templates */
      if (_.isEmpty(templates)) {
        return <row />;
      }
      return (
        <row>
          <column size='12'>
            <label>Configure plugin</label>
            <select onChange={this.handleSelect}>
              {_.keys(templates).map(function(plugin) {
                return <option key={plugin} value={plugin}>{_.capitalize(plugin)}</option>;
              })}
            </select>
            <input id="check-advanced" type="checkbox" value={this.state.advancedOpts}
                    onChange={this.toggleAdvanced} />
            <label htmlFor="check-advanced">Show advanced options</label>
            {/* NOTE: This is kind of nasty.... We can't use _'s 'partial',
                      since we want to provide the second argument and leave
                      the first one to the caller. */}
            <PluginWidget plugin={selectedPlugin}
                          template={templates[selectedPlugin]}
                          showAdvanced={this.state.advancedOpts}
                          bindFunc={function(key) {
                            return this.bindTo(
                              this.props.workflow,
                              'config.' + selectedPlugin + '.' + key);
                          }.bind(this)}
                          errors={this.props.errors}/>
          </column>
        </row>
      );
    }
  });

  module.exports = {
      PluginWidget: PluginWidget,
      PluginConfiguration: PluginConfiguration
  }


}());

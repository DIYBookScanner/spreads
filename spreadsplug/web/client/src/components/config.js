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
      F = require('./foundation.js'),
      util = require('../util.js'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      capitalize = require('../util.js').capitalize;


  /**
   * A single option component for the workflow configuration.
   */
  var PluginOption = React.createClass({
    propTypes: {
      /** Name of the option */
      name: React.PropTypes.string.isRequired,
      /** Current value of the option */
      value: React.PropTypes.oneOfType([
        React.PropTypes.string,
        React.PropTypes.number,
        React.PropTypes.bool,
      ]).isRequired,
      /** Template for the option */
      option: React.PropTypes.object.isRequired,
      /** Errors from server-side validation for the option */
      error: React.PropTypes.object,
      /** Function to be called when value changes */
      onChange: React.PropTypes.func.isRequired
    },

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
        return null;
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
      var isSmall = util.isSmall();
      var isCheckbox = input.props.type === 'checkbox';

      if (isSmall) {
        return (
          <div>
            <F.Row>
              {isCheckbox &&
                <F.Column size={1}>
                  {input}
                </F.Column>}
              <F.Column size={isCheckbox ? 11 : 12}>
                {label}
              </F.Column>
            </F.Row>
            {!isCheckbox &&
            <F.Row><F.Column>{input}{error}</F.Column></F.Row>}
          </div>);
      } else {
        return (
          <F.Row>
          {input &&
            <F.Column>
              <F.Row>
              {/* Labels are to the left of all inputs, except for checkboxes */}
              {input.props.type === 'checkbox' ?
                <F.Column size={1}>{input}</F.Column> : <F.Column size={5}>{label}{error}</F.Column>}
              {input.props.type === 'checkbox' ?
                <F.Column size={11}>{label}</F.Column> : <F.Column size={7}>{input}{error}</F.Column>}
              </F.Row>
            </F.Column>}
          </F.Row>
        );
      }
    }
  });


  /**
   * Collection of options for a single plugin
   */
  var PluginWidget = React.createClass({
    propTypes: {
      /** Whether to show advanced options */
      showAdvanced: React.PropTypes.bool,
      /** Current settings for this plugin */
      cfgValues: React.PropTypes.object.isRequired,
      /** Template for the settings */
      template: React.PropTypes.object.isRequired,
      /** Errors from server-side validation */
      errors: React.PropTypes.object,
      /** Function to be called when value changes */
      onChange: React.PropTypes.func.isRequired
    },

    /** Generate change callback for a given key */
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


  /**
   * Component for selecting plugin to display settings for
   */
  var PluginSelector = React.createClass({
    propTypes: {
      /** Type of plugins to select */
      type: React.PropTypes.string.isRequired,
      /** List of available plugins of that type */
      available: React.PropTypes.arrayOf(React.PropTypes.string).isRequired,
      /** Function to be called when selection changes */
      onChange: React.PropTypes.func.isRequired,
      /** List of enabled plugins of that type */
      enabled: React.PropTypes.arrayOf(React.PropTypes.string)
    },

    render: function() {
      var checkboxes = _.map(this.props.available, function(plugin) {
        var key = 'toggle-' + plugin;
        return (
          <F.Row key={key}>
            <F.Column>
              <input id={key} type="checkbox"
                    checked={_.contains(this.props.enabled, plugin)}
                    onChange={function(e){
                        this.props.onChange(e.target.checked, plugin);
                    }.bind(this)} />
              <label htmlFor={key}> {plugin} </label>
            </F.Column>
          </F.Row>);
      }, this);
      var selectLabel = <label>Select {this.props.type} plugins</label>;

      if (util.isSmall()) {
        return (
          <div className="plugin-select">
            <F.Row className="plugin-select-label">
              <F.Column>{selectLabel}</F.Column>
            </F.Row>
            {checkboxes}
          </div>);
      } else {
        return (
          <F.Row className="plugin-select">
            <F.Column className="plugin-select-label" size={3}>
              {selectLabel}
            </F.Column>
            <F.Column size={9} className="select-pane">
              {checkboxes}
            </F.Column>
          </F.Row>);
      }
    }
  });


  var SectionSelector = React.createClass({
    propTypes: {
      active: React.PropTypes.bool,
      onClick: React.PropTypes.func.isRequired,
      name: React.PropTypes.string.isRequired
    },

    render: function() {
      var classes = React.addons.classSet({
        "plugin-label": true,
        active: this.props.active
      });
      return (
        <F.Row>
          <F.Column>
            <a onClick={this.props.onClick}>
              <label className={classes}>
                {capitalize(this.props.name)}
                {this.props.active &&
                 <i style={{"margin-right": "1rem",
                            "line-height": "inherit"}}
                    className="fa fa-caret-right right" />}
              </label>
            </a>
          </F.Column>
        </F.Row>);
    }
  });


  /**
   * Container for all plugin configuration widgets.
   * Offers a dropdown to select a plugin to configure and displays its
   * configuration widget.
   */
  var PluginConfiguration = React.createClass({
    propTypes: {
      /** Available plugins by type */
      availablePlugins: React.PropTypes.object,
      /** Current configuration */
      config: React.PropTypes.object,
      /** Configuration templates for available plugins */
      templates: React.PropTypes.object.isRequired,
      /** Errors from server-side validation */
      errors: React.PropTypes.object
    },

    getDefaultProps: function() {
      var availablePlugins;
      if (!_.isUndefined(window.plugins)) {
        if (window.config.mode == 'scanner') {
          availablePlugins = _.omit(window.plugins, "postprocessing", "output");
        } else {
          availablePlugins = window.plugins;
        }
      } else if (_.isUndefined(availablePlugins)) {
        availablePlugins = {};
      }

      return {
        availablePlugins: availablePlugins,
        config: {plugins: _.flatten(availablePlugins)}
      };
    },

    getInitialState: function() {
      return {
        /** Currently selected plugin */
        selectedSection: undefined,
        /** Validation errors (from components themselves */
        internalErrors: {},
        /** Only for initialization purposes, not intended to be kept in sync
         *  at all times. */
        config: this.props.config || {plugins: _.flatten(this.props.availablePlugins)},
        /** Whether to display advanced options */
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

      configSections = _.filter(config.plugins, function(plugin) {
          return !_.isEmpty(templates[plugin]);
      });

      if (window.config.web.mode !== 'processor' &&
          !_.isEmpty(templates['device'])) {
          configSections.push('device');
      }

      /* If no section is explicitely selected, use the first one */
      selectedSection = this.state.selectedSection;
      if (!_.isEmpty(configSections) && !selectedSection) {
        selectedSection = configSections[0];
      }

      var isSmall = util.isSmall();
      var sectionPicker;
      var paneContainer = isSmall ? F.Row : React.DOM.div;
      var outerContainer = isSmall ? React.DOM.div : F.Row;
      if (util.isSmall()) {
        sectionPicker = (
          <F.Row className="section-picker">
            <F.Column>
              <select multiple={false} value={selectedSection}
                      onChange={function(e) {
                        this.setState({selectedSection: e.target.value});
                      }.bind(this)}>
                {_.map(configSections, function(section) {
                  return <option key={section} value={section}>{capitalize(section)}</option>;
                })}
              </select>
              <div><i className="fa fa-caret-down down" /></div>
            </F.Column>
          </F.Row>
        );
      } else {
        sectionPicker = (
          <F.Column size={3} className="section-picker">
            {_.map(configSections, function(section) {
              return (
              <SectionSelector key={section} active={selectedSection === section} name={section}
                               onClick={_.partial(this.setState.bind(this), {selectedSection: section}, null)} />);
            }, this)}
          </F.Column>
        )
      }

      return (
        <F.Row>
          <F.Column size={[12, 10, 8]}>
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
              <F.Row className="toggle-advanced">
                <F.Column>
                  <input id="check-advanced" type="checkbox" value={this.state.advancedOpts}
                          onChange={this.toggleAdvanced} />
                  <label htmlFor="check-advanced">Show advanced options</label>
                </F.Column>
              </F.Row>
              <outerContainer className="plugin-config">
                {sectionPicker}
                <paneContainer>
                  <F.Column size={[12, 9]} className="config-pane">
                    <PluginWidget template={templates[selectedSection]}
                                  showAdvanced={this.state.advancedOpts}
                                  cfgValues={this.state.config[selectedSection] || this.getDefaultConfig(selectedSection)}
                                  errors={errors[selectedSection] || {}}
                                  onChange={_.partial(this.handleChange, selectedSection)} />
                  </F.Column>
                </paneContainer>
              </outerContainer>
            </fieldset>
          </F.Column>
        </F.Row>);
    }
  });

  module.exports = {
      PluginWidget: PluginWidget,
      PluginConfiguration: PluginConfiguration
  }
}());

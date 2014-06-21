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
      jQuery = require('jquery'),
      foundation = require('./foundation.js'),
      ProgressOverlay = require('./overlays.js').Progress,
      PluginWidget = require('./config.js').PluginWidget,
      PluginConfiguration = require('./config.js').PluginConfiguration,
      row = foundation.row,
      column = foundation.column;

  module.exports = React.createClass({
    displayName: "SubmissionForm",

    getInitialState: function() {
      return {
        selectedServer: undefined,
        availableServers: [],
        plugins: {},
        templates: {},
        workflow: undefined,
        /** Errors from validation */
        errors: {},
        submissionWaiting: false,
        submissionProgress: 0,
      };
    },
    componentDidMount: function() {
      jQuery.getJSON('/api/remote/discover', function(data) {
        if (data.servers.length > 0) {
          this.setState({
            availableServers: data.servers,
            selectedServer: data.servers[0]
          }, this.loadServerData);
        }
      }.bind(this));
    },
    loadServerData: function() {
      // NOTE: To take advantage of the things Backbone provides, we clone
      // our workflow here. **This clone is never persisted**
      var workflow = this.props.workflow.clone(),
          config = {};

      // Clear errors
      this.setState({errors: {}});


      function loadTemplates() {
        jQuery.getJSON(
          '/api/remote/plugins/templates',
          {'server': this.state.selectedServer},
          function(data) {
            var config = this.state.config,
                plugins = this.state.plugins['postprocessing'].concat(this.state.plugins['output']);
            this.setState({
              templates: data
            });
            _.each(plugins, function(plugName) {
              this.loadDefaultConfig(plugName);
            }, this);
          }.bind(this))
          .fail(function(xhr) {
            this.setState({
              errors: xhr.responseJSON.errors
            });
            console.error("Could not get list of remote templates");
          }.bind(this));
      }

      jQuery.getJSON(
        '/api/remote/plugins',
        {'server': this.state.selectedServer},
        function(data) {
          config.plugins = data.postprocessing.concat(data.output);
          workflow.set('config', config);
          this.setState({
            plugins: data,
            workflow: workflow
          });
          loadTemplates.bind(this)()
          /* Update `errors` if there were validation errors. */
          workflow.on('validated:invalid', function(workflow, errors) {
            this.setState({errors: errors});
          }, this);
        }.bind(this))
        .fail(function(xhr) {
          this.setState({
            errors: xhr.responseJSON.errors
          });
          console.error("Could not get list of remote plugins");
        }.bind(this));
    },
    handleSubmit: function() {
      console.debug(this.state);
      if (!_.isEmpty(this.state.errors) || !this.state.workflow) {
        return;
      }
      var start_process,
          start_output,
          selected_plugins = this.state.workflow.get('config').plugins;
      start_process = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.plugins.postprocessing, plugName);
      }, this);
      start_output = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.plugins.output, plugName);
      }, this);
      jQuery.ajax('/api/workflow/' + this.props.workflow.id + '/submit', {
        type: 'POST',
        data: JSON.stringify(
          { config: this.state.workflow.get('config'),
            start_process: start_process,
            start_output: start_output,
            server: this.state.selectedServer }),
        contentType: "application/json; charset=utf-8",
      }).fail(function(xhr) {
        this.setState({ submissionWaiting: false });
      }.bind(this));
      this.setState({
        submissionWaiting: true,
        submissionProgress: 0,
        submissionCurrentFile: undefined
      });
      window.router.events.on('submit:progressed', function(data) {
        if (this.isMounted()) {
          this.setState({
            submissionProgress: data.progress*100 | 0,
            submissionCurrentFile: data.status
          });
        }
      }.bind(this))
      window.router.events.on('submit:completed', function() {
        /*
        this.setState({
          submissionWaiting: false
        });
        */
        window.router.navigate('/', {trigger: true});
      }.bind(this));
    },
    handleServerSelect: function(event) {
      this.setState({
        plugins: {},
        templates: {},
        selectedServer: event.target.value
      }, this.loadServerData);
    },
    handlePluginToggle: function(enabled, pluginName) {
      var config = this.state.workflow.get('config');
      if (enabled) {
        config.plugins.push(pluginName);
        this.loadDefaultConfig(pluginName);
      } else {
        config.plugins = _.without(config.plugins, pluginName);
        delete config[pluginName];
      }
      this.state.workflow.set('config', config);
      this.forceUpdate();
    },
    handlePluginSelect: function(event) {
      this.setState({
        selectedPlugin: event.target.value
      });
    },
    loadDefaultConfig: function(pluginName) {
      if (_.has(this.state.templates, pluginName)) {
        var template = this.state.templates[pluginName],
            config = this.state.workflow.get('config');
        config[pluginName] = {};
        _.each(template, function(option, key) {
          config[pluginName][key] = option.value;
        });
        this.state.workflow.set('config', config);
        this.forceUpdate();
      }
    },
    render: function() {
      return (
        <section>
          <form onSubmit={this.handleSubmit}>
            {this.state.submissionWaiting &&
              <ProgressOverlay progress={this.state.submissionProgress}
                               statusMessage={this.state.submissionCurrentFile || "Preparing submission..."}/>}
            <row>
              <column size='12'>
                <h2>Configure postprocessing</h2>
              </column>
            </row>
            {this.state.availableServers.length > 0 &&
            <row>
              <column size={[12,9]}>
                <label className={this.state.errors.server ? 'error': ''}>
                  Select postprocessing server
                  <select onChange={this.handleServerSelect}
                          className={this.state.errors.server ? 'error': ''}>
                    {this.state.availableServers.map(function(server) {
                      return <option key={server} value={server}>{server}</option>;
                    })}
                  </select>
                </label>
              </column>
            </row>}
            <row>
              <column size={12}>
                <row collapse={true}>
                  <column size={[10,7]}>
                    <input type="text" placeholder="Custom server address"
                          className={this.state.errors.server ? 'error': ''}
                          onKeyUp={function(e){
                            // Check for enter key
                            if (e.keyCode == 13) this.handleServerSelect(e);
                          }.bind(this)}
                          onBlur={this.handleServerSelect} />
                    {this.state.errors.server &&
                    <small className="error">{this.state.errors.server}</small>}
                  </column>
                  <column size={[2, 5]}>
                    <a className="button postfix" style={{width: '8em'}}><i className="fa fa-refresh"/> Refresh</a>
                  </column>
                </row>
              </column>
            </row>
            {this.state.selectedServer &&
            <div>
            <row>
              <column size={[12,9]}>
                {this.state.plugins && _.map(this.state.plugins.postprocessing, function(plugin) {
                  var key = 'toggle-' + plugin;
                  return (
                    <div key={key}>
                      <input id={key} type="checkbox" defaultChecked={true}
                            onChange={function(e){this.handlePluginToggle(e.target.checked, plugin);}.bind(this)} />
                      <label htmlFor={key}> {plugin} </label>
                    </div>
                  );
                }.bind(this))}
              </column>
            </row>
            <row>
              <column size={[12,9]}>
                {this.state.plugins && _.map(this.state.plugins.output, function(plugin) {
                  var key = 'toggle-' + plugin;
                  return (
                    <div key={key}>
                      <input id={key} type="checkbox" defaultChecked={true}
                              onChange={function(e) {this.handlePluginToggle(e.target.checked, plugin)}.bind(this)}/>
                      <label htmlFor={key}>{plugin}</label>
                    </div>
                  );
                }.bind(this))}
              </column>
            </row>
            {(this.state.workflow && !_.isEmpty(this.state.templates)) &&
            <PluginConfiguration workflow={this.state.workflow}
                                 errors={this.state.errors}
                                 templates={this.state.templates} />}
            <row>
              <column size={[12,9]}>
                <button className={_.isEmpty(this.state.errors) ? '': 'disabled'}>Submit</button>
              </column>
            </row>
          </div>
          }
          </form>
          </section>
      );
    }
  });
}());

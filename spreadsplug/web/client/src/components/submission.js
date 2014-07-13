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
        availablePlugins: {},
        configTemplates: {},
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
      // Clear errors
      this.setState({errors: {}});

      function loadTemplates() {
        jQuery.getJSON(
          '/api/remote/plugins/templates',
          {'server': this.state.selectedServer},
          function(data) {
            this.setState({
              configTemplates: data
            });
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
          this.setState({
            availablePlugins: data
          });
          loadTemplates.bind(this)()
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
      if (!_.isEmpty(this.state.errors) || !this.props.workflow) {
        return;
      }
      var start_process,
          start_output,
          config = this.refs.configuration.state.config,
          selected_plugins = config.plugins;
      start_process = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.availablePlugins.postprocessing, plugName);
      }, this);
      start_output = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.availablePlugins.output, plugName);
      }, this);
      jQuery.ajax('/api/workflow/' + this.props.workflow.id + '/submit', {
        type: 'POST',
        data: JSON.stringify(
          { config: config,
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
        window.router.navigate('/', {trigger: true});
      }.bind(this));
    },
    handleServerSelect: function(event) {
      this.setState({
        plugins: {},
        selectedServer: event.target.value
      }, this.loadServerData);
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
            {this.state.selectedServer && this.props.workflow &&
             !_.isEmpty(this.state.configTemplates) &&
            <div>
              <PluginConfiguration ref="configuration"
                                   config={this.props.workflow.get('config')}
                                   errors={this.state.errors || {}}
                                   templates={this.state.configTemplates}
                                   availablePlugins={this.state.availablePlugins} />
              <row>
                <column size={[12,9]}>
                  <button className={_.isEmpty(this.state.errors) ? '': 'disabled'}>
                    Submit
                  </button>
                </column>
              </row>
            </div>}
          </form>
        </section>);
    }
  });
}());

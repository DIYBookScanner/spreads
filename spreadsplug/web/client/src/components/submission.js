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
      F = require('./foundation.js'),
      util = require('../util.js'),
      ProgressOverlay = require('./overlays.js').Progress,
      LayeredComponentMixin = require('./overlays.js').LayeredComponentMixin,
      PluginWidget = require('./config.js').PluginWidget,
      PluginConfiguration = require('./config.js').PluginConfiguration;

  var SubmissionForm = React.createClass({
    mixins: [LayeredComponentMixin],

    propTypes: {
      workflow: React.PropTypes.object.isRequired
    },

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

    handleSubmitSuccess: function() {
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

    handleSubmit: function() {
      console.debug(this.state);
      if (!_.isEmpty(this.state.errors) || !this.props.workflow) {
        return;
      }
      var startProcess,
          startOutput,
          config = this.refs.configuration.state.config,
          selected_plugins = config.plugins;
      startProcess = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.availablePlugins.postprocessing, plugName);
      }, this);
      startOutput = _.some(selected_plugins, function(plugName) {
        return _.contains(this.state.availablePlugins.output, plugName);
      }, this);
      this.props.workflow.submit({
        config: config,
        startProcess: startProcess,
        startOutput: startOutput,
        server: this.state.selectedServer,
        onSuccess: this.handleSubmitSuccess.bind(this),
        onError: function() {
          this.setState({ submissionWaiting: false });
        }.bind(this)
      });
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
            <F.Row>
              <F.Column>
                <h2>Configure postprocessing</h2>
              </F.Column>
            </F.Row>
            {this.state.availableServers.length > 0 &&
            <F.Row>
              <F.Column size={[12,9]}>
                <label className={this.state.errors.server ? 'error': ''}>
                  Select postprocessing server
                  <select onChange={this.handleServerSelect}
                          className={this.state.errors.server ? 'error': ''}>
                    {this.state.availableServers.map(function(server) {
                      return <option key={server} value={server}>{server}</option>;
                    })}
                  </select>
                </label>
              </F.Column>
            </F.Row>}
            <F.Row>
              <F.Column size={[12, 9]}>
                <F.Row collapse={true}>
                  <F.Column size={[9,10]}>
                    <input type="text" placeholder="Custom server address"
                          className={this.state.errors.server ? 'error': ''}
                          onKeyUp={function(e){
                            // Check for enter key
                            if (e.keyCode == 13) this.handleServerSelect(e);
                          }.bind(this)}
                          onBlur={this.handleServerSelect} />
                    {this.state.errors.server &&
                    <small className="error">{this.state.errors.server}</small>}
                  </F.Column>
                  <F.Column size={[3, 2]}>
                    <a className="button postfix"><i className="fa fa-refresh"/> {!util.isSmall() && 'Refresh'}</a>
                  </F.Column>
                </F.Row>
              </F.Column>
            </F.Row>
            {this.state.selectedServer && this.props.workflow &&
             !_.isEmpty(this.state.configTemplates) &&
            <div>
              <PluginConfiguration ref="configuration"
                                   config={this.props.workflow.get('config')}
                                   errors={this.state.errors || {}}
                                   templates={this.state.configTemplates}
                                   availablePlugins={this.state.availablePlugins} />
              <F.Row>
                <F.Column size={[12,9]}>
                  <button className={_.isEmpty(this.state.errors) ? '': 'disabled'}>
                    Submit
                  </button>
                </F.Column>
              </F.Row>
            </div>}
          </form>
        </section>);
    },

    renderLayer: function() {
      if (this.state.submissionWaiting) {
        return (
          <ProgressOverlay progress={this.state.submissionProgress}
                           statusMessage={this.state.submissionCurrentFile || "Preparing submission..."}/>);
      }
    }
  });

  module.exports = SubmissionForm;
}());

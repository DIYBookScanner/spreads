/** @jsx React.DOM */
/* global require, module */

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
      WorkflowForm = require('./workflowform'),
      CaptureScreen = require('./capture').CaptureScreen,
      WorkflowDetails = require('./workflow'),
      WorkflowList = require('./workflowlist').WorkflowList,
      SubmissionForm = require('./submission'),
      NavigationBar = require('./navbar'),
      LogDisplay = require('./logdisplay.js'),
      F = require('./foundation');  // Shorthand for Foundation components


  /**
   * Core application component.
   *
   * Handles selection of display components and error messages.
   *
   * @property {Backbone.Collection<Workflow>} [workflows] - Associated workflows
   * @property {string} [workflowSlug] - Associated workflow slug
   * @property {string} view - Name of view to display
   */
  var SpreadsApp = React.createClass({
    propTypes: {
      workflows: React.PropTypes.object.isRequired,
      workflowSlug: React.PropTypes.string,
      view: React.PropTypes.string
    },

    componentWillMount: function() {
      this.updateViewComponent(this.props);
    },

    /** Register message change listeners */
    componentDidMount: function() {
      window.router.events.on('logrecord', function(record) {
        if (_.contains(["WARNING", "ERROR"], record.level)) {
          this.setState({
            numUnreadErrors: this.state.numUnreadErrors + 1
          });
        }
      }, this);
      window.router.on('route:displayLog', function() {
        this.setState({messages: [], numUnreadErrors: 0});
      }, this);
      window.router.events.on('apierror', function(eror) {
        this.setState({
          messages: this.state.messages.concat([error.message]).slice(-3)
        });
      });
    },

    componentWillUnmount: function() {
      window.router.events.off('logrecord', null, this);
      window.router.off(null, null, this);
    },

    componentWillReceiveProps: function(nextProps) {
      this.updateViewComponent(nextProps);
    },

    getInitialState: function() {
      return {
        messages: [],
        numUnreadErrors: 0,
        viewComponent: null
      };
    },

    /**
     * Get title for navigation bar.
     *
     * @param {string} viewName - name of current view
     * @return {string} The title for the navigation bar
     */
    getNavTitle: function(viewName) {
      var mappings = {
        create:       "spreads: new workflow",
        capture:      "spreads: capture",
        view:         "spreads: workflow details",
        edit:         "spreads: edit workflow",
        root:         "spreads: workflow list"
      };
      if (mappings[viewName] !== undefined) {
        return mappings[viewName];
      } else {
        return "spreads";
      }
    },

    /**
     * Get view component to render.
     *
     * @param {string} viewName - name of current view
     * @return {React.Component} The component to render
     */
    updateViewComponent: function(props) {
      var workflows = props.workflows;
      var displayed = props.workflowSlug && workflows.where({slug: props.workflowSlug})[0];
      var viewName = props.view;
      var viewComponent;

      if (viewName === 'create') {
        var newWorkflow = new workflows.model();
        workflows.add(newWorkflow);
        viewComponent = <WorkflowForm workflow={newWorkflow} isNew={true}/>;
      } else if (viewName === "capture") {
        viewComponent = <CaptureScreen workflow={displayed} />;
      } else if (viewName === "view") {
        viewComponent = <WorkflowDetails workflow={displayed} />;
      } else if (viewName === "edit") {
        viewComponent = <WorkflowForm workflow={displayed} isNew={false} />;
      } else if (viewName === "submit") {
        viewComponent = <SubmissionForm workflow={displayed} />;
      } else if (viewName === "log") {
        viewComponent = <LogDisplay />;
      } else {
        viewComponent = <WorkflowList workflows={workflows}/>;
      }
      this.setState({
        viewComponent: viewComponent
      });
    },

    /**
     * Get a callback to close a given message
     *
     * @param {Message} message - The message to close in the callback
     * @return {function} - A callback function that closes the `message`.
     */
    getCloseMessageCallback: function(message) {
      return function() {
        this.setState({
          messages: _.without(this.state.messages, message),
          numUnreadErrors: this.state.numUnreadErrors - 1
        });
      }.bind(this);
    },

    render: function() {
      var navTitle = this.getNavTitle(this.props.view);
      var msgLevelMapping = {
        'critical': 'alert',
        'error': 'alert',
        'warning': 'warning',
        'info': 'standard',
        'debug': 'secondary'
      };
      document.title = navTitle;
      return (
        <div>
          <NavigationBar title={navTitle} numUnreadErrors={this.state.numUnreadErrors}/>
          {this.state.messages && this.state.messages.map(function(message) {
            return (
                <F.Alert severity={msgLevelMapping[message.level.toLowerCase()]}
                         key={new Date(message.time).getTime()}
                         onClick={this.getCloseMessageCallback(message)}>
                  {message.message}
                </F.Alert>);
            })}
          {this.state.viewComponent}
        </div>
      );
    }
  });

  module.exports = SpreadsApp;
}());

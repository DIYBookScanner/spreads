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
      CaptureInterface = require('./capture'),
      WorkflowDetails = require('./workflow'),
      WorkflowList = require('./workflowlist'),
      NavigationBar = require('./navbar'),
      LogDisplay = require('./logdisplay.js'),
      fnAlert = require('./foundation').alert;

  /**
   * Core application component.
   *
   * Handles selection of display components and error messages.
   *
   * @property {Backbone.Collection<Workflow>} [workflows] - Associated workflows
   * @property {number} [workflowId] - Associated workflow ID
   * @property {string} view - Name of view to display
   */
  module.exports = React.createClass({
    displayName: "SpreadsApp",

    /** Register message change listeners */
    componentDidMount: function() {
      // TODO: Listen for logging events, filter by level
      window.router.events.on('logrecord', function(record) {
        if (_.contains(["WARNING", "ERROR"], record.level)) {
          this.setState({
            messages: this.state.messages.concat([record]).slice(-3),
            numUnreadErrors: this.state.numUnreadErrors + 1
          });
        }
      }, this);
      window.router.on('route:displayLog', function() {
        this.setState(this.getInitialState());
      }, this);
    },
    componentWillUnmount: function() {
      window.router.events.off('logrecord', null, this);
    },
    getInitialState: function() {
      return {
        messages: [],
        numUnreadErrors: 0
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
        preferences:  "spreads: preferences",
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
    getViewComponent: function(viewName) {
      var workflows = this.props.workflows,
          workflowId = this.props.workflowId;
      switch (viewName) {
      case "create":
        var newWorkflow = new workflows.model(null, {collection: workflows});
        return <WorkflowForm workflow={newWorkflow} isNew={true}/>;
      case "capture":
        return <CaptureInterface workflow={workflows.get(workflowId)}/>;
      case "view":
        return <WorkflowDetails workflow={workflows.get(workflowId)}/>;
      case "edit":
        return <WorkflowForm workflow={workflows.get(workflowId)} isNew={false} />;
      case "log":
        return <LogDisplay />;
      default:
        return <WorkflowList workflows={workflows}/>;
      }
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
      var navTitle = this.getNavTitle(this.props.view),
          viewComponent = this.getViewComponent(this.props.view);
      document.title = navTitle;
      return (
        <div>
          <NavigationBar title={navTitle} numUnreadErrors={this.state.numUnreadErrors}/>
          {this.state.messages &&
              this.state.messages.map(function(message) {
                return (
                    <fnAlert level={message.level}
                             message={message.message}
                             key={new Date(message.time).getTime()}
                             closeCallback={this.getCloseMessageCallback(message)}>
                    </fnAlert>);
              }, this)}
          {viewComponent}
        </div>
      );
    }
  });
}());

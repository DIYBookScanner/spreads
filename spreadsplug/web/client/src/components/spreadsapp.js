/** @jsx React.DOM */
/* global require, module */
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
    /** Register message change listeners */
    componentDidMount: function() {
      // TODO: Listen for logging events, filter by level
      window.router.events.on('logrecord', function(record) {
        if (_.contains(["WARNING", "ERROR"], record.level)) {
          this.setState({messages: this.state.messages.concat([record])});
        }
      }, this);
    },
    componentWillUnmount: function() {
      window.router.events.off('logrecord', null, this);
    },
    getInitialState: function() {
      return {
        messages: []
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
        view:         "spreads: details"
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
        return <WorkflowForm workflow={newWorkflow}/>;
      case "capture":
        return <CaptureInterface workflow={workflows.get(workflowId)}/>;
      case "view":
        return <WorkflowDetails workflow={workflows.get(workflowId)}/>;
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
        this.setState({messages: _.without(this.state.messages, message)});
      }.bind(this);
    },
    render: function() {
      var navTitle = this.getNavTitle(this.props.view),
          viewComponent = this.getViewComponent(this.props.view);
      return (
        <div>
          <NavigationBar title={navTitle} />
          {this.state.messages &&
              this.state.messages.map(function(message) {
                return (
                    <fnAlert level={message.level}
                             message={message.message}
                             key={new Date(message.time).getTime()}
                             closeCallback={this.getCloseMessageCallback(message)}>
                      <a className="right" href='#/log'>(View detailed log)</a>
                    </fnAlert>);
              }, this)}
          {viewComponent}
        </div>
      );
    }
  });
}());

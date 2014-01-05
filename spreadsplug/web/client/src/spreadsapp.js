/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';

  var React = require('react'),
      WorkflowForm = require('./workflowform'),
      CaptureInterface = require('./capture'),
      PreferencesForm = require('./preferences'),
      WorkflowDetails = require('./workflow'),
      WorkflowList = require('./workflowlist')
      NavigationBar = require('./navbar');

  module.exports = React.createClass({
    loadWorkflow: function(workflowId) {
      // TODO: Load workflow via AJAX
    },
    getNavTitle: function(viewName) {
      var mappings = {
        "create":       "spreads: new workflow",
        "capture":      "spreads: capture",
        "preferences":  "spreads: preferences",
        "view":         "spreads: details"
      };
      if (mappings[viewName] !== undefined) {
          return mappings[viewName];
      } else {
        return "spreads";
      }
    },
    getViewComponent: function(viewName) {
      var workflow;
      if (this.props.workflow !== undefined) {
        workflow = this.loadWorkflow(this.props.workflow);
      }
      if (viewName === "create") {
        return (<WorkflowForm />); // jshint ignore:line
      } else if (viewName === "capture") {
        return (<CaptureInterface workflow={workflow}/>); // jshint ignore:line
      } else if (viewName === "preferences") {
        return (<PreferencesForm />); // jshint ignore:line
      } else if (viewName === "view") {
        return (<WorkflowDetails workflow={workflow}/>); // jshint ignore:line
      } else {
        return (<WorkflowList />); // jshint ignore:line
      }
    },
    render: function() {
      var navTitle = this.getNavTitle(),
          viewComponent = this.getViewComponent();
      // jshint ignore:start
      return (<div>
                <NavigationBar title={navTitle} />
                <viewComponent />
              </div>);
      // jshint ignore:end
    }
  });
}());

/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';

  var React = require('react/addons'),
      WorkflowForm = require('./workflowform'),
      CaptureInterface = require('./capture'),
      PreferencesForm = require('./preferences'),
      WorkflowDetails = require('./workflow'),
      WorkflowList = require('./workflowlist'),
      NavigationBar = require('./navbar');

  module.exports = React.createClass({
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
    getViewComponent: function(viewName) {
      var workflows = this.props.workflows,
          workflowId = this.props.workflowId;
      /* jshint ignore:start */
      switch (viewName) {
        case "create":
          var newWorkflow = workflows.add([{}])[0];
          return <WorkflowForm workflow={newWorkflow}/>;
        case "capture":
          return <CaptureInterface workflow={workflows.get(workflowId)}/>;
        case "preferences":
         return  <PreferencesForm />;
        case "view":
          return <WorkflowDetails workflow={workflows.get(workflowId)}/>;
        case "root":
        default:
          return <WorkflowList workflows={workflows}/>;
      };
      /* jshint ignore:end */
    },
    render: function() {
      var navTitle = this.getNavTitle(this.props.view),
          viewComponent = this.getViewComponent(this.props.view);
      // TODO: Handle case where this.props.workflows === undefined
      /* jshint ignore:start */
      return (<div>
                <NavigationBar title={navTitle} />
                {viewComponent}
              </div>);
      /* jshint ignore:end */
    }
  });
}());

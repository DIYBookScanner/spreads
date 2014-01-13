/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var Backbone = require('backbone'),
      React = require('react/addons'),
      SpreadsApp = require('./components/spreadsapp'),
      Workflows = require('./workflow.js');

  module.exports = Backbone.Router.extend({
    initialize: function() {
      this._workflows = new Workflows();
      this._workflows.fetch({async: false});
    },
    routes: {
      "":                       "root",
      "workflow/new":           "createWorkflow",
      "workflow/:id":          "viewWorkflow",
      "workflow/:id/capture":  "startCapture",
      "preferences":            "editPreferences"
    },
    _renderView: function(view, workflow) {
      React.renderComponent(<SpreadsApp view={view} workflows={this._workflows}
                                        workflowId={workflow}/>,
                            document.getElementById('content'));
    },
    root: function() {
      this._renderView("root");
    },
    createWorkflow: function() {
      this._renderView("create");;
    },
    viewWorkflow: function(workflowId) {
      this._renderView("view", workflowId);
    },
    startCapture: function(workflowId) {
      this._renderView("capture", workflowId);
    },
    editPreferences: function() {
      this._renderView("preferences");
    }
  });
}());

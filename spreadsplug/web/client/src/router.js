/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';
  var Backbone = require('backbone'),
      SpreadsApp = require('./spreadsapp');

  module.exports = Backbone.Router.extend({
    routes: {
      "/":                      "root",
      "workflow/new":           "createWorkflow",
      "workflow/:id:":          "viewWorkflow",
      "workflow/:id:/capture":  "startCapture",
      "preferences":            "editPreferences"
    },

    renderView: function(view, workflow_id) {
      /* jshint ignore:start */
      React.renderComponent(<SpreadsApp view={view} workflow={workflow_id}/>,
                            document.getElementById('content'));
      /* jshint ignore:end */
    },

    root: function() {
      this._renderView("root");
    },

    createWorkflow: function() {
      this._renderView("create");
    },

    viewWorkflow: function(workflow_id) {
      this._renderView("view", workflow_id);
    },

    startCapture: function(workflow_id) {
      this._renderView("capture", workflow_id);
    },

    editPreferences: function() {
      this._renderView("preferences");
    }
  });
}());

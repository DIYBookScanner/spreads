/** @jsx React.DOM */
/* global module, require, console */
(function() {
  'use strict';
  var Backbone = require('backbone'),
      React = require('react/addons'),
      _ = require('underscore'),
      jQuery = require('jquery'),
      SpreadsApp = require('./components/spreadsapp'),
      Workflows = require('./workflow.js'),
      events = require('./events.js');

  /**
   * Application Router.
   * Defines which view names correspond to which route and updates the
   * `SpreadsApp` root container with the new view and optionally a workflow
   * id.
   */
  module.exports = Backbone.Router.extend({
    /**
     * Sets up the application.
     */
    initialize: function() {
      this.events = events;

      // Set up model collections
      this._workflows = new Workflows();
      this._workflows.connectEvents(this.events);

      // Get workflows synchronously from server
      this._workflows.fetch({async: false});
    },
    routes: {
      "":                       "root",
      "workflow/new":           "createWorkflow",
      "workflow/:id":           "viewWorkflow",
      "workflow/:id/edit":      "editWorkflow",
      "workflow/:id/capture":   "startCapture",
      "preferences":            "editPreferences",
      "logging":                "displayLog"
    },
    /**
     * Renders `SpreadsApp` component into `content` container and assigns
     * the passed `view` name and `workflow` id as well as our model
     * collection (`this._workflows`).
     *
     * @private
     * @param {string} view
     * @param {?number} workflowId
     */
    _renderView: function(view, workflowId) {
      React.renderComponent(<SpreadsApp view={view} workflows={this._workflows}
                                        workflowId={workflowId} />,
                            document.getElementById('content'));
    },
    root: function() {
      this._renderView("root");
    },
    createWorkflow: function() {
      this._renderView("create");
    },
    viewWorkflow: function(workflowId) {
      this._renderView("view", workflowId);
    },
    editWorkflow: function(workflowId) {
      this._renderView("edit", workflowId);
    },
    startCapture: function(workflowId) {
      this._renderView("capture", workflowId);
    },
    editPreferences: function() {
      this._renderView("preferences");
    },
    displayLog: function() {
      this._renderView("log");
    }
  });
}());

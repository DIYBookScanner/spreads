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
      Messages = require('./messages.js');

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
      // Set up model collections
      this._workflows = new Workflows();
      this._messages = new Messages();

      // Get workflows synchronously from server
      this._workflows.fetch({async: false});

      // Start long-polling for updates
      this._startPolling();
    },
    routes: {
      "":                       "root",
      "workflow/new":           "createWorkflow",
      "workflow/:id":           "viewWorkflow",
      "workflow/:id/capture":   "startCapture",
      "preferences":            "editPreferences",
      "log":                    "displayLog"
    },
    /**
     * Renders `SpreadsApp` component into `content` container and assigns
     * the passed `view` name and `workflow` id as well as our model
     * collections (`this._workflows`, `this._messages`).
     *
     * @private
     * @param {string} view
     * @param {?number} workflowId
     */
    _renderView: function(view, workflowId) {
      React.renderComponent(<SpreadsApp view={view} workflows={this._workflows}
                                        workflowId={workflowId}
                                        messages={this._messages} />,
                            document.getElementById('content'));
    },
    /**
     * Starts long-polling the server for updates on workflow and message
     * model collections.
     */
    _startPolling: function() {
      (function poll() {
        jQuery.ajax({
            url: "/poll",
            success: function(data){
              if (data.messages.length) {
                console.debug("Updating messages.");
                this._messages.set(data.messages);
              }
              if (data.workflows.length) {
                console.debug("Updating workflows.");
                this._workflows.add(data.workflows, {merge: true});
              }
            }.bind(this),
            dataType: "json",
            complete: function(xhr, status) {
              if (_.contains(["timeout", "success"], status)) {
                // Restart polling
                poll.bind(this)();
              } else {
                // Back off for 30 seconds before polling again
                _.delay(poll.bind(this), 30*1000);
              }
            }.bind(this),
            timeout: 30*1000  // Cancel the request after 30 seconds
          });
      }.bind(this)());
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

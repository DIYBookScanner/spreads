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

  module.exports = Backbone.Router.extend({
    initialize: function() {
      this._workflows = new Workflows();
      this._messages = new Messages();
      this._workflows.fetch({async: false});
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
    _renderView: function(view, workflow) {
      React.renderComponent(<SpreadsApp view={view} workflows={this._workflows}
                                        workflowId={workflow}
                                        messages={this._messages} />,
                            document.getElementById('content'));
    },
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
                poll.bind(this)();
              } else {
                _.delay(poll.bind(this), 30*1000);
              }
            }.bind(this),
            timeout: 30*1000
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

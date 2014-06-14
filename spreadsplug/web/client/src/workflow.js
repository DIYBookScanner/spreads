/* global module, require, console */

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

  var Backbone = require('backbone'),
      _ = require('underscore'),
      jQuery = require('jquery'),
      Workflow;
  // Custom third party extension to Backbone, see below
  Backbone.DeepModel = require('../vendor/backbone-deep-model.js');
  // Load Backbone.Validation extension
  require('backbone-validation');
  _.extend(Backbone.DeepModel.prototype, Backbone.Validation.mixin);

  /* We extend DeepModel instead of Model so we can listen on changes for
   * nested objects like workflow.config. */
  Workflow = Backbone.DeepModel.extend({
    initialize: function() {
      this._setPluginValidators();
      if (this.isNew()) {
        this._setDefaultConfiguration();
      }
    },
    validation: {
      name: {
        required: true,
        // All printable ASCII characters, except '/' and '''
        pattern: /^[\x20-\x27\x29-\x2E\x30-\x7E]*$/,
        msg: 'Please enter a valid name (ASCII only and no "/" or "\'")'
      }
    },
    validate: function() {
      // NOTE: We monkey patch the stupid Backbone.Validation mixin, as it
      // pretends as if validation is always successful...
      return Backbone.Validation.mixin.validate.bind(this)();
    },
    /**
     * Initiates the submission of the workflow to a remote postprocessing
     * server for postprocessing and output generation.
     *
     * @param {requestCallback} callback Callback to execute after API request
     *                                   is completed.
     */
    submit: function(callback) {
      console.log("Submitting workflow " + this.id + " for postprocessing");
      jQuery.post('/api/workflow/' + this.id + '/submit')
        .fail(function() {
          console.error("Could not submit workflow " + this.id);
        }).complete(callback);
    },
    /**
     * Initiates the transfer to a removable storage device.
     *
     * @param {requestCallback} callback Callback to execute after API request is
     *                                   completed.
     */
    transfer: function(callback) {
      console.log("Initiating transfer for workflow " + this.id + "");
      jQuery.post('/api/workflow/' + this.id + '/transfer')
        .fail(function() {
          console.error("Could not transfer workflow " + this.id);
        }).complete(callback);
    },
    /**
     * Prepares devices for capture.
     *
     * @param {requestCallback} callback Callback to execute after API request is
     *                                   completed.
     */
    prepareCapture: function(callback, reset) {
      jQuery.post(
        '/api/workflow/' + this.id + '/prepare_capture' + (reset ? '?reset=true' : ''),
        function() {
          console.log("Preparation successful");
        }.bind(this)).fail(function() {
          console.error("Capture preparation failed");
        }).complete(callback);
    },
    /**
     * Triggers a capture.
     *
     * @param {boolean} retake Discard the previous shot and retake it
     * @param {requestCallback} callback Callback to execute after API request is
     *                                   completed.
     */
    triggerCapture: function(retake, callback) {
      jQuery.post(
        '/api/workflow/' + this.id + "/capture" + (retake ? '?retake=true' : ''),
        function(data) {
          console.log("Capture succeeded");
          //this.addPages(data.pages);
          // Since no 'real' update of the pages takes place during a
          // retake, but we would like to update the dependant views anyway
          // to get the latest versions of the pages, we force a 'change'
          // event.
          if (retake) {
            this.trigger('change');
            this.trigger('change:pages', this.get('pages'));
          }
        }.bind(this)).fail(function() {
          console.error("Capture failed");
        }).complete(callback);
    },
    /**
     * Indicate the end of the capture process to the server.
     *
     * @param {requestCallback} callback Callback to execute after API request is
     *                                   completed.
     */
    finishCapture: function(callback) {
      jQuery.post('/api/workflow/' + this.id + "/finish_capture", function() {
        console.log("Capture successfully finished");
      }).fail(function() {
        console.error("Capture could not be finished.");
      }).complete(callback);
    },
    addPages: function(pages) {
      var modified = false;
      _.each(pages, function(page) {
        if (!_.contains(this.get('pages'), page)) {
          this.get('pages').push(page);
          modified = true;
        }
      }, this);
      if (modified) {
        this.trigger('change');
        this.trigger('change:pages', this.get('pages'));
      }
    },
    deletePages: function(pages, callback) {
      jQuery.ajax('/api/workflow/' + this.id + '/page', {
        type: 'DELETE',
        contentType: 'application/json',
        data: JSON.stringify({pages: pages})
      }).fail(function() {
        console.error("Could not remove pages from workflow.");
      }).done(function(data) {
        var oldPages = _.clone(this.get('pages')),
            newPages = _.difference(oldPages, data.pages);
        this.set({"pages": newPages});
      }.bind(this));
    },
    cropPage: function(pageNum, cropParams, callback) {
      var parts = [];
      for (var p in cropParams)
          parts.push(encodeURIComponent(p) + "=" + encodeURIComponent(cropParams[p]));

      jQuery.post('/api/workflow/' + this.id + '/page/' + pageNum + '/raw/crop?' + parts.join("&"))
        .fail(function() {
          console.error("Could not crop page " + pageNum);
        });
    },
    /**
     * Set default configuration from our global `pluginTemplates` object.
     *
     * @private
     */
    _setDefaultConfiguration: function() {
      var templates = window.pluginTemplates;
      _.each(templates, function(template, plugin) {
        _.each(template, function(option, name) {
          var path = 'config.' + plugin + '.' + name;
          if (option.selectable) {
            this.set(path, option.value[0]);
          } else {
            this.set(path, option.value);
          }
        }, this);
      }, this);
    },
    /**
     * Auto-generate Backbone validators for our configuration fields from
     * the global `pluginTemplates` object.
     *
     * @private
     */
    _setPluginValidators: function() {
      var templates = window.pluginTemplates;
      _.each(templates, function(template, plugin) {
        _.each(template, function(option, name) {
          var path = 'config.' + plugin + '.' + name;
          if (option.selectable) {
            this.validation[path] = {
              oneOf: option.value
            };
          } else if (_.isNumber(option.value)) {
            this.validation[path] = {
              pattern: 'number',
              msg: 'Must be a number.'
            };
          }
        }, this);
      }, this);
    }
  });

  module.exports = Backbone.Collection.extend({
    model: Workflow,
    url: '/api/workflow',
    connectEvents: function(eventDispatcher) {
      eventDispatcher.on('workflow:created', function(data) {
        // Check for pending workflows, if there is one, it's the one that
        // just triggered the event on the server and is just about to receive
        // its data from the POST response
        // => Only add from an event if it wasn't us wo created the workflow
        if (this.where({id: undefined}).length != 1) {
          this.add(data.workflow);
        }
      }, this);
      eventDispatcher.on('workflow:removed', function(workflowId) {
        var workflow = this.get(workflowId);
        if (workflow) {
          this.remove(workflow);
        }
      }, this);
      eventDispatcher.on('workflow:capture-triggered', function(data) {
        var workflow = this.get(data.id);
        if (workflow) {
          workflow.trigger('capture-triggered');
        }
      }, this);
      eventDispatcher.on('workflow:capture-succeeded', function(data) {
        var workflow = this.get(data.id);
        if (workflow) {
          workflow.addPages(data.pages);
          workflow.trigger('capture-succeeded', data);
        }
      }, this);
      eventDispatcher.on('workflow:status-updated', function(data) {
        var workflow = this.get(data.id);
        if (workflow) {
          workflow.set('status', data.status);
        }
      });
    }
  });
}());

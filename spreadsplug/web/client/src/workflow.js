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
          this.addImages(data.images);
          // Since no 'real' update of the images takes place during a
          // retake, but we would like to update the dependant views anyway
          // to get the latest versions of the images, we force a 'change'
          // event.
          if (retake) {
            this.trigger('change');
            this.trigger('change:images', this.get('images'));
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
    addImages: function(images) {
      var modified = false;
      _.each(images, function(img) {
        if (!_.contains(this.get('images'), img)) {
          this.get('images').push(img);
          modified = true;
        }
      }, this);
      if (modified) {
        this.trigger('change');
        this.trigger('change:images', this.get('images'));
      }
    },
    deleteImage: function(imageUrl, callback) {
      var imgNum = imageUrl.split('/').splice(-1)[0];
      jQuery.ajax('/api/workflow/' + this.id + '/image/' + imgNum, {
        type: 'DELETE',
      }).fail(function() {
        console.error("Could not remove image " + imgNum + " from workflow.");
      }).done(function() {
        var imageIdx = this.get('images').indexOf(imageUrl);
        this.get('images').splice(imageIdx, 1);
        this.trigger('change');
        this.trigger('change:images', this.get('images'));
      }.bind(this));
    },
    cropImage: function(imageUrl, cropParams, callback) {
      var parts = [];
      for (var p in cropParams)
          parts.push(encodeURIComponent(p) + "=" + encodeURIComponent(cropParams[p]));

      jQuery.post(imageUrl + '/crop?' + parts.join("&"))
        .fail(function() {
          console.error("Could not crop image " + imageUrl );
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

  /**
   * Callback for API requests. Executed after the request finished, no
   * matter if successfull or unsuccessful.
   *
   * @param {jQuery.xhr} xhr - The XHTTPRequest object
   * @param {string} xhr - The request tatus
   */

  module.exports = Backbone.Collection.extend({
    model: Workflow,
    url: '/api/workflow',
    connectEvents: function(eventDispatcher) {
      eventDispatcher.on('workflow:created', function(workflow) {
        if (!this.contains(workflow)) {
          this.add(workflow);
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
          workflow.addImages(data.images)
          workflow.trigger('capture-succeeded');
        }
      }, this);
    }
  });
}());

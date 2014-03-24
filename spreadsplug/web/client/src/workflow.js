/* global module, require, console */
(function() {
  'use strict';

  var Backbone = require('backbone'),
      _ = require('underscore'),
      jQuery = require('jquery'),
      Workflow;
  // Custom third party extension to Backbone, see below
  Backbone.DeepModel = require('../lib/backbone-deep-model.js');
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
        // All printable ASCII characters, except '/'
        pattern: /^[\x20-\x2E\x30-\x7E]*$/,
        msg: 'Non-ASCII characters and "/" are not permitted.'
      }
    },
    validate: function() {
      // NOTE: We monkey patch the stupid Backbone.Validation mixin, as it
      // pretends as if validation is always successful...
      return Backbone.Validation.mixin.validate.bind(this)();
    },
    /**
     * Initiates the submissiong of the workflow to a remote postprocessing
     * server for postprocessing and output generation.
     *
     * @param {requestCallback} callback Callback to execute after API request
     *                                   is completed.
     */
    submit: function(callback) {
      console.debug("Submitting workflow " + this.id + " for postprocessing");
      jQuery.post('/workflow/' + this.id + '/submit')
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
      console.debug("Initiating transfer for workflow " + this.id + "");
      jQuery.post('/workflow/' + this.id + '/transfer')
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
    prepareCapture: function(callback) {
      jQuery.post(
        '/workflow/' + this.id + '/prepare_capture',
        function() {
          console.debug("Preparation successful");
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
        '/workflow/' + this.id + "/capture" + (retake ? '?retake=true' : ''),
        function(data) {
          console.debug("Capture succeeded");
          if (retake) {
            // Since the model will not change (number of images and names
            // don't change) we have to manually trigger a 'change' event
            // to force a re-render of the bound components.
            this.trigger('change');
          } else {
            // Add image objects from response to the model
            this.set('images', this.get('images').concat(data.images));
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
      jQuery.post('/workflow/' + this.id + "/finish_capture", function() {
        console.debug("Capture successfully finished");
      }).fail(function() {
        console.error("Capture could not be finished.");
      }).complete(callback);
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
    url: '/workflow'
  });
}());

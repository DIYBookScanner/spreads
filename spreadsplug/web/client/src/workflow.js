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
    // Don't synchronize these with the server
    blacklist: ['configuration_template'],
    toJSON: function() {
        return _.omit(this.attributes, this.blacklist);
      },
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
    submit: function(callback) {
      console.debug("Submitting workflow " + this.id + " for postprocessing");
      jQuery.post('/workflow/' + this.id + '/submit')
        .fail(function() {
          console.error("Could not submit workflow " + this.id);
        }).complete(callback);
    },
    queue: function(callback) {
      jQuery.post('/queue', {id: this.id}, function(data) {
          this.queueId = data.queue_position;
        }).complete(callback);
    },
    dequeue: function(callback) {
      jQuery.ajax({
        type: "DELETE",
        url: '/queue/' + this.queueId,
      }).fail(function() {
        console.error("Could not delete workflow " + this.id + " from queue");
      }).complete(callback);
    },
    prepareCapture: function(callback) {
      jQuery.post(
        '/workflow/' + this.id + '/prepare_capture',
        function() {
          console.debug("Preparation successful");
        }.bind(this)).fail(function() {
          console.error("Capture preparation failed");
        }).complete(callback);
    },
    triggerCapture: function(retake, callback) {
      jQuery.post(
        '/workflow/' + this.id + "/capture" + (retake ? '?retake=true' : ''),
        function(data) {
          console.debug("Capture succeeded");
          if (retake) {
            this.trigger('change');
          } else {
            this.set('images', this.get('images').concat(data.images));
          }
        }.bind(this)).fail(function() {
          console.error("Capture failed");
        }).complete(callback);
    },
    finishCapture: function(callback) {
      jQuery.post('/workflow/' + this.id + "/finish_capture", function() {
        console.debug("Capture successfully finished");
      }).fail(function() {
        console.error("Capture could not be finished.");
      }).complete(callback);
    },
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
    url: '/workflow'
  });
}());

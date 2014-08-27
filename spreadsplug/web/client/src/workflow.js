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
      util = require('./util.js'),
      Workflow;
      _.mixin(require('underscore.deep'));

  // Custom third party extension to Backbone, see below
  Backbone.DeepModel = require('backbone-deep-model').DeepModel;

  /* We extend DeepModel instead of Model so we can listen on changes for
   * nested objects like workflow.config. */
  Workflow = Backbone.DeepModel.extend({
    /**
     * Initiates the submission of the workflow to a remote postprocessing
     * server for postprocessing and output generation.
     */
    submit: function(options) {
      var options = options || {};
      jQuery.ajax('/api/workflow/' + this.id + '/submit', {
          type: 'POST',
          data: {
            config: options.config,
            start_process: options.startProcess,
            start_output: options.startOutput,
            server: options.server
          },
          contentType: "application/json; charset=utf-8"})
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    /**
     * Initiates the transfer to a removable storage device.
     */
    transfer: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + '/transfer')
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    /**
     * Prepares devices for capture.
     */
    prepareCapture: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + '/prepare_capture' + (options.reset ? '?reset=true' : ''))
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    /**
     * Triggers a capture.
     */
    triggerCapture: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + "/capture" + (options.retake ? '?retake=true' : ''))
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(function(data) {
          // Since no 'real' update of the pages takes place during a
          // retake, but we would like to update the dependant views anyway
          // to get the latest versions of the pages, we force a 'change'
          // event.
          if (options.retake) {
            this.trigger('change');
            this.trigger('change:pages', this.get('pages'));
          }
          if (options.onSuccess) options.onSuccess(data);
        }.bind(this));
    },

    /**
     * Indicate the end of the capture process to the server.
     */
    finishCapture: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + "/finish_capture")
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    startPostprocessing: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + '/process')
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    startOutputting: function(options) {
      var options = options || {};
      jQuery.post('/api/workflow/' + this.id + '/output')
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },

    deletePages: function(options) {
      var options = options || {};
      if (_.isEmpty(options.pages)) return;
      jQuery.ajax('/api/workflow/' + this.id + '/page', {
          type: 'DELETE',
          contentType: 'application/json',
          data: JSON.stringify({pages: options.pages})
        })
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(function(data) {
          var oldPages = _.clone(this.get('pages')),
              newPages = _.difference(oldPages, data.pages);
          this.set({"pages": newPages});
          if (options.onSuccess) options.onSuccess(data);
        }.bind(this));
    },

    cropPage: function(options) {
      var options = options || {};
      var parts = [];
      for (var p in options.cropParams)
          parts.push(encodeURIComponent(p) + "=" + encodeURIComponent(options.cropParams[p]));

      jQuery.post('/api/workflow/' + this.id + '/page/' + options.pageNum + '/raw/crop?' + parts.join("&"))
        .fail(function(xhr) {
          if (options.onError) options.onError(xhr.responseJSON);
        })
        .done(options.onSuccess || util.noop);
    },
  });

  module.exports = Backbone.Collection.extend({
    model: Workflow,
    url: '/api/workflow',
    comparator: function(workflow) {
      return -workflow.get('last_modified');
    },
    connectEvents: function(eventDispatcher) {
      eventDispatcher.on('workflow:created', function(data) {
        // Check for pending workflows, if there is one, it's the one that
        // just triggered the event on the server and is about to receive
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
        var workflow = this.get(data.senderId);
        if (workflow) {
          workflow.trigger('capture-triggered');
        }
      }, this);
      eventDispatcher.on('workflow:capture-succeeded', function(data) {
        var workflow = this.get(data.senderId);
        if (workflow) {
          workflow.trigger('capture-succeeded', data);
        }
      }, this);
      eventDispatcher.on('workflow:capture-failed', function(data) {
        var workflow = this.get(data.senderId);
        if (workflow) {
          workflow.trigger('capture-failed', data);
        }
      }, this);
      eventDispatcher.on('workflow:modified', function(data) {
        var workflow = this.get(data.senderId);
        var changes = data.changes;
        changes.last_modified = new Date().getTime() / 1000;
        if (workflow) {
          workflow.set(changes);
        }
        this.sort();
      }, this);
    }
  });
}());

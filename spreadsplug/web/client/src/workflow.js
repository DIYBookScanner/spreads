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
      _.mixin(require('underscore.deep'));

  // Custom third party extension to Backbone, see below
  Backbone.DeepModel = require('backbone-deep-model').DeepModel;

  /* We extend DeepModel instead of Model so we can listen on changes for
   * nested objects like workflow.config. */
  Workflow = Backbone.DeepModel.extend({
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
        .fail(function(xhr) {
          console.error("Could not submit workflow " + this.id);
          this.emitError(xhr.responseText);
        }.bind(this)).complete(callback);
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
        .fail(function(xhr) {
          console.error("Could not transfer workflow " + this.id);
          this.emitError(xhr.responseText);
        }.bind(this)).complete(callback);
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
        }.bind(this)).fail(function(xhr) {
          console.error("Capture preparation failed");
          this.emitError(xhr.responseText);
        }.bind(this)).complete(callback);
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
        }.bind(this)).fail(function(xhr) {
          console.error("Capture failed");
          this.emitError(xhr.responseText);
        }.bind(this)).complete(callback);
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
      }).fail(function(xhr) {
        console.error("Capture could not be finished.");
        this.emitError(xhr.responseText);
      }.bind(this)).complete(callback);
    },
    startPostprocessing: function(callback) {
      jQuery.post('/api/workflow/' + this.id + '/process', function() {
        console.log("Postprocessing started.");
      }).fail(function(xhr) {
        console.log("Failed to start postprocessing.");
        this.emitError(xhr.responseText);
      }.bind(this)).complete(callback);
    },
    startOutputting: function(callback) {
      jQuery.post('/api/workflow/' + this.id + '/output', function() {
        console.log("Output generation started.");
      }).fail(function(xhr) {
        console.log("Failed to start output generation.");
        this.emitError(xhr.responseText);
      }.bind(this)).complete(callback);
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
      }).fail(function(xhr) {
        this.emitError(xhr.responseText);
        console.error("Could not remove pages from workflow.");
      }.bind(this)).done(function(data) {
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
        .fail(function(xhr) {
          console.error("Could not crop page " + pageNum);
          this.emitError(xhr.responseText);
        }.bind(this));
    },
    emitError: function(error) {
      var obj;
      try {
        obj = jQuery.parseJSON(error);
      } catch (e) {
        obj = {message: error}
      }
      window.router.events.trigger('apierror', obj);
    }
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
        var workflow = this.get(data.id);
        if (workflow) {
          workflow.trigger('capture-triggered');
        }
      }, this);
      eventDispatcher.on('workflow:capture-succeeded', function(data) {
        var workflow = this.get(data.id);
        if (workflow) {
          workflow.trigger('capture-succeeded', data);
        }
      }, this);
      eventDispatcher.on('workflow:modified', function(data) {
        var workflow = this.get(data.id);
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

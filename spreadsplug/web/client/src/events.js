/*global require, module, console */

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
      websocket;

  var LongPollingMixin = {
    errorSleepTime: 500,
    cursor: null,

    poll: function() {
        var args = {};
        if (this.cursor) args.cursor = this.cursor;
        jQuery.ajax({url: "/api/poll", type: "POST", dataType: "text",
                data: jQuery.param(args), success: this.onSuccess.bind(this),
                error: this.onError.bind(this)});
    },

    onSuccess: function(response) {
        try {
            this.newEvents(eval("(" + response + ")"));
        } catch (e) {
            this.onError();
            return;
        }
        this.errorSleepTime = 500;
        window.setTimeout(this.poll.bind(this), 0);
    },

    onError: function(response) {
        this.errorSleepTime *= 2;
        console.log("Poll error; sleeping for", this.errorSleepTime, "ms");
        window.setTimeout(this.poll, this.errorSleepTime);
    },

    newEvents: function(response) {
        if (!response.events) return;
        this.cursor = response.cursor;
        var events = response.events;
        this.cursor = events[events.length - 1].id;
        console.log(events.length, "new events, cursor:", this.cursor);
        for (var i = 0; i < events.length; i++) {
            this.emitEvent(events[i]);
        }
    }
  }

  var EventDispatcher = function() {
    if (window.MozWebSocket) {
      window.WebSocket = window.MozWebSocket;
    }
    if (window.WebSocket) {
      var hostName = window.location.hostname,
          port = parseInt(window.location.port) || 80;
      websocket = new WebSocket("ws://" + hostName + ":" + port + "/ws");
      websocket.onclose = function() {
        if (!websocket.onmessage) {
          // This means we were never able to establish a connection,
          // probably because the websocket server is not accessible, so
          // we fall back to long-polling.
          console.warn("Could not open connection to WebSocket server " +
                        "at " + websocket.url + ", falling back to " +
                        "long polling.");
          this.poll();
        }
      }.bind(this);
      websocket.onopen = function() {
        // Start listening to server events
        websocket.onmessage = function(messageEvent) {
          this.emitEvent(JSON.parse(messageEvent.data));
        }.bind(this);
      }.bind(this);
    } else {
      // Use AJAX long-polling as a fallback when WebSockets are not supported
      // by the browser
      this.poll();
    }
  };

  _.extend(EventDispatcher.prototype, Backbone.Events, LongPollingMixin, {
    emitEvent: function emitEvent(event) {
      if (event.name !== 'logrecord' && window.config.web.debug) {
        console.log(event.name, event.data);
      }
      this.trigger(event.name, event.data);
    },
  });

  module.exports = EventDispatcher;
}());

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
      websocket, EventDispatcher;

  EventDispatcher = function() {
    if (window.MozWebSocket) {
      window.WebSocket = window.MozWebSocket;
    }
    if (window.WebSocket) {
      // Try to use WebSockets
      var hostName = window.location.hostname,
          port = parseInt(window.location.port)+1;
      websocket = new WebSocket("ws://" + hostName + ":" + port);
      websocket.onclose = function() {
        if (!websocket.onmessage) {
          // This means we were never able to establish a connection,
          // probably because the websocket server is not accessible, so
          // we fall back to long-polling.
          console.warn("Could not open connection to WebSocket server " +
                        "at " + websocket.url + ", falling back to " +
                        "long polling.");
          this.longPoll();
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
      this.longPoll();
    }
  };

  _.extend(EventDispatcher.prototype, Backbone.Events, {
    emitEvent: function emitEvent(event) {
      if (event.name !== 'logrecord' && window.config.web.debug) console.log(event.name, event.data);
      this.trigger(event.name, event.data);
    },
    longPoll: function longPoll() {
      jQuery.ajax({
        url: "/api/poll",
        success: function(data){
          _.each(data, this.emitEvent, this);
        }.bind(this),
        dataType: "json",
        complete: function(xhr, status) {
          if (_.contains(["timeout", "success"], status)) {
            // Restart polling
            this.longPoll();
          } else {
            // Back off for 30 seconds before polling again
            _.delay(this.longPoll.bind(this), 30*1000);
          }
        }.bind(this),
        timeout: 30*1000  // Cancel the request after 30 seconds
      });
    }
  });

  module.exports = EventDispatcher;
}());

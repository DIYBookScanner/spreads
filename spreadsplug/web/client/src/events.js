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
      websocket,
      eventDispatcher;

  eventDispatcher = _.clone(Backbone.Events);

  function emitEvent(event) {
    var parts = event.name.split(':')
    if (parts[0] === 'workflow:' && parts[1] !== 'created') {
        event.name = parts[0] + event.data.id + ':' + parts[1];
        delete event.data['id'];
    }
    eventDispatcher.trigger(event.name, event.data);
  }

  function longPoll() {
    jQuery.ajax({
      url: "/api/poll",
      success: function(data){
        _.each(data, emitEvent);
      },
      dataType: "json",
      complete: function(xhr, status) {
        if (_.contains(["timeout", "success"], status)) {
          // Restart polling
          longPoll();
        } else {
          // Back off for 30 seconds before polling again
          _.delay(longPoll, 30*1000);
        }
      },
      timeout: 30*1000  // Cancel the request after 30 seconds
    });
  }

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
        longPoll();
      }
    }.bind(this);
    websocket.onopen = function() {
      // Start listening to server events
      websocket.onmessage = function(messageEvent) {
        emitEvent(JSON.parse(messageEvent.data));
      };
    }.bind(this);
  } else {
    // Use AJAX long-polling as a fallback when WebSockets are not supported
    // by the browser
    longPoll();
  }

  module.exports = eventDispatcher;
}());

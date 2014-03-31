/*global require, module, console */
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
      url: "/poll",
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
    websocket = new WebSocket("ws://"+window.location.hostname+":5001/");
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

/* global require */
(function() {
  'use strict';

  var Backbone = require('backbone'),
      $ = require('jquery'),
      Router = require('./router');

  // Assign jQuery to Backbone
  Backbone.$ = $;
  // Assign jQuery to window for Foundation
  /** @global */
  window.jQuery = $;

  // Initialize routing
  /** @global */
  window.router = new Router();
  Backbone.history.start();
}());

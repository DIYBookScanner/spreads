/* global require */
(function() {
  'use strict';

  var Backbone = require('backbone'),
      $ = require('jquery')(window),
      Router = require('./router');

  // Assign jQuery to Backbone
  Backbone.$ = $;
  // Assign jQuery to window for Foundation
  window.jQuery = $;

  // Initialize routing
  window.router = new Router();
  Backbone.history.start();
}());

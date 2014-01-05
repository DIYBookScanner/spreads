/** @jsx React.DOM */
/* global require, document */
(function() {
  'use strict';

  var  React = require('react'),
  Backbone = require('backbone'),
  $ = require('jquery'),
  SpreadsApp = require('./spreadsapp'),
  Workspace = require('./router');

  // Initialize routing
  var router = new Workspace();
  Backbone.history.start();

  // Start foundation javascript
  $(document).foundation();

  // Render component
  React.renderComponent(<SpreadsApp view="root" />, document.getElementById('content')); // jshint ignore:line
}());

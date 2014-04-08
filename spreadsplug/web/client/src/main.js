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

  window.React = require('react');

  // Initialize routing
  /** @global */
  window.router = new Router();
  Backbone.history.start({pushState: true, root: '/'});

  // Intercept the browser's default link handling
  $(document).on('click', 'a:not([data-bypass])', function(e) {
    var href = $(this).attr('href');
    if (!href) {
      return;
    }
    var protocol = this.protocol + '//';
    if (href.slice(protocol.length) !== protocol) {
      e.preventDefault();
      window.router.navigate(href, true);
    }
  });

  // Intercept the browser's default form submissino handling
  $(document).on('submit', 'form', function(e) {
    e.preventDefault();
  });
}());

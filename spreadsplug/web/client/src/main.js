/* global require */

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
      jQuery = require('jquery'),
      Router = require('./router'),
      React = require('react/addons');

  // Load stylesheets
  require('../scss/app.scss');
  require('../vendor/foundation-icons.css');
  require("imports?this=>window,Modernizr=../src/util.js,jQuery=jquery!../vendor/foundation.js");
  require("imports?this=>window,Modernizr=../src/util.js,jQuery=jquery!../vendor/foundation.topbar.js");

  // Assign jQuery to Backbone
  Backbone.$ = jQuery;

  // For debugging with the React chrome addon
  window.React = React;

  // Initialize routing
  /** @global */
  window.router = new Router();
  Backbone.history.start({pushState: true, root: '/'});

  // Initialize foundation
  jQuery(document).foundation();

  // Initialize touch events in React
  React.initializeTouchEvents();

  // Intercept the browser's default link handling
  jQuery(document).on('click', 'a:not([data-bypass])', function(e) {
    var href = jQuery(this).attr('href');
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
  jQuery(document).on('submit', 'form', function(e) {
    e.preventDefault();
  });
}());

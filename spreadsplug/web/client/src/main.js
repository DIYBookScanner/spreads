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

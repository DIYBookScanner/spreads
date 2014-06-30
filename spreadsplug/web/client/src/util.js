/* global module, require, matchMedia, Foundation */

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

  /* TODO: These are currently copy-pasta'ed from Foundation, it would be nice
   *       to properly load foundation via 'require' to determine these
   *       at runtime. */
  var mediaQueries = {
    large: "only screen and (min-width:64.063em)",
    medium: "only screen and (min-width:40.063em)",
    small: "only screen",
    topbar: "only screen and (min-width:40.063em)",
    xlarge: "only screen and (min-width:90.063em)",
    xxlarge: "only screen and (min-width:120.063em)"
  };

  function isTouchDevice() {
    return 'ontouchstart' in window || 'onmsgesturechange' in window;
  }

  function isSmall() {
    return matchMedia(mediaQueries.small).matches &&
      !matchMedia(mediaQueries.medium).matches;
  }

  function getOrientation() {
    return (window.innerHeight > window.innerWidth) ? 'portrait' : 'landscape';
  }

  /**
    * Convert the first letter of a given string to uppercase.
    *
    * @param {string} string
    */
  function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.substring(1).toLowerCase();
  }

  function getPageUrl(workflow, page, type, thumb) {
    var url = "/api/workflow/" + workflow.id + "/page/" + page.sequence_num;
    if (page) {
      if (type !== 'raw') type = 'processed/' + type;
      url = url + "/" + type;
    }
    if (thumb) url = url + "/thumb";
    return url;
  }

  module.exports = {
    isTouchDevice: isTouchDevice,
    isSmall: isSmall,
    getOrientation: getOrientation,
    mediaQueries: mediaQueries,
    capitalize: capitalize,
    // For modernizr compatibility
    touch: isTouchDevice(),
    getPageUrl: getPageUrl
  }
}());

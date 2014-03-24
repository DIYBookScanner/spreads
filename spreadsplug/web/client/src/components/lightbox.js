/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons');

  /**
   * Display image in lightbox overlay.
   *
   * @property {function} onClose - Callback function for when the lightbox is closed.
   * @property {url} src - Source URL for the image to be displayed
   */
  module.exports = React.createClass({
    render: function() {
      return (
        <a onClick={this.props.onClose} className="lightbox">
          <img src={this.props.src} />
        </a>
      );
    }
  });
}());

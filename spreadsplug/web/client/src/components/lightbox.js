/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      _ = require('underscore');

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

/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons');

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

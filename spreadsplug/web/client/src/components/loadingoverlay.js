/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons');

  module.exports = React.createClass({
    render: function() {
      return (
        <div className="overlay">
          <div className="spinner">
            <div className="double-bounce1"></div>
            <div className="double-bounce2"></div>
          </div>
          <p className="text">{this.props.message}</p>
        </div>
      );
    }
  });
}());

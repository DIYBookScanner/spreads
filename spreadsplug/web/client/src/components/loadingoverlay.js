/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      Spinner = require('spin.js');

  module.exports = React.createClass({
    getInitialState: function() {
      return {spinner: this._getSpinner()};
    },
    componentDidMount: function() {
      this.state.spinner.spin(this.getDOMNode());
    },
    componentWillUnmount: function() {
      this.state.spinner.stop();
    },
    _getSpinner: function() {
      return new Spinner();
    },
    render: function() {
      return (
        <div className="overlay">
          <div className="circle">
          </div>
          <p className="text">
              {this.props.message}
          </p>
        </div>
      );
    }
  });
}());

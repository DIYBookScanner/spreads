/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';
  var React = require('react/addons');

  module.exports = {
    row: React.createClass({
      render: function() {
        /* jshint ignore:start */
        return (<div className="row">{this.props.children}</div>);
        /* jshint ignore:end */
      }
    }),
    column: React.createClass({
      render: function() {
        var classes;
        if (typeof this.props.size === 'object') {
          var sizes = this.props.size;
          classes = "small-" + sizes[0] +
                    " medium-" + sizes[1] +
                    " large-" + (sizes[2] || sizes[1])+
                    " columns";
        } else {
          classes = "small-" + this.props.size + " columns";
        }
        /* jshint ignore:start */
        return (<div className={classes}>{this.props.children}</div>);
        /* jshint ignore:end */
      }
    }),
    button: React.createClass({
      render: function() {
        /* jshint ignore:start */
        return (<a onClick={this.props.callback}
                   className={(this.props.size + ' ' || '')
                              + "button"
                              + (this.props.secondary ? " secondary" : '')}>
                  {this.props.children}
                </a>
               );
        /* jshint ignore:end */
      }
    })
  };
}());

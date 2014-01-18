/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      _ = require('underscore');

  module.exports = {
    row: React.createClass({
      render: function() {
        return (<div className="row">{this.props.children}</div>);
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
          classes = "small-" + (this.props.size || 12) + " columns";
        }
        return (<div className={classes}>{this.props.children}</div>);
      }
    }),
    button: React.createClass({
      render: function() {
        return (<a onClick={this.props.callback}
                   className={(this.props.size + ' ' || '') +
                              "button" +
                              (this.props.secondary ? " secondary" : '')}>
                  {this.props.children}
                </a>
               );
      }
    }),
    alert: React.createClass({
      handleClose: function() {
        this.props.closeCallback();
      },
      render: function() {
        var classes = ['alert-box'];
        if (_.contains(['WARNING', 'ERROR'], this.props.level)) {
          classes.push('warning');
        }
        return (<div data-alert
                     className={"alert-box " + classes.join(' ')} >
                  {this.props.message}
                  <a onClick={this.handleClose} className="close">&times;</a>
                </div>
               );
      }
    })
  };
}());

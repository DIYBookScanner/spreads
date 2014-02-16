/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      jQuery = require('jquery');

  module.exports = React.createClass({
    doShutdown: function() {
      // TODO: Ask for confirmation
      // TODO: Show activity indicator until connection has died
      // TODO: Make UI inactive until polling is successful again
      jQuery.ajax({
        type: "POST",
        url: "/system/shutdown"
      });
    },
    render: function() {
      return (
        <div className="contain-to-grid fixed">
          <nav className="top-bar" data-topbar>
            <ul className="title-area">
              <li className="name"> <h1><a href="#/">{this.props.title}</a></h1> </li>
              <li className="toggle-topbar"><a href="#" className="fi-list"></a></li>
            </ul>
            <section className="top-bar-section">
              <ul className="left">
                <li><a href="#/workflow/new"><i className="fi-plus"></i> New workflow</a></li>
              </ul>
              <ul className="right">
                <li><a href="#/preferences"><i className="fi-widget"></i> Preferences</a></li>
                <li><a onClick={this.doShutdown}><i className="fi-power"></i> Shut down</a></li>
              </ul>
            </section>
          </nav>
        </div>
      );
    }
  });
}());

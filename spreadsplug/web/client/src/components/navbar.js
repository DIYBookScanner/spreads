/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons');

  module.exports = React.createClass({
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
              </ul>
            </section>
          </nav>
        </div>
      );
    }
  });
}());

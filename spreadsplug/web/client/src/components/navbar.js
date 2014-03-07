/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      jQuery = require('jquery'),
      confirmModal = require('./foundation.js').confirmModal;

  module.exports = React.createClass({
    getInitialState: function() {
      return {
        shutdownModal: false
      };
    },
    doShutdown: function() {
      // TODO: Show activity indicator until connection has died
      // TODO: Make UI inactive until polling is successful again
      jQuery.ajax({
        type: "POST",
        url: "/system/shutdown"
      });
      this.setState({
        shutdownModal: false
      });
    },
    handleShutdown: function() {
      this.setState({
        shutdownModal: true
      });
    },
    render: function() {
      return (
        <div className="contain-to-grid fixed">
          {this.state.shutdownModal &&
            <confirmModal
              onCancel={function(){this.setState({shutdownModal: false});}.bind(this)}
              onConfirm={this.doShutdown}>
              <h1>Shut down</h1>
              <p>Do you really want to shut down the device?</p>
            </confirmModal>}
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
                {window.config.standalone_device &&
                  (<li><a onClick={this.handleShutdown}><i className="fi-power"></i> Shut down</a></li>)}
              </ul>
            </section>
          </nav>
        </div>
      );
    }
  });
}());

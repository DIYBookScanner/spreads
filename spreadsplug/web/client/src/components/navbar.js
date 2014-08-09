/** @jsx React.DOM */
/* global module, require */

/*
 * Copyright (C) 2014 Johannes Baiter <johannes.baiter@gmail.com>
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.

 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

(function() {
  'use strict';
  var React = require('react/addons'),
      jQuery = require('jquery'),
      modal = require('./foundation.js').modal,
      F = require('./foundation.js');

  /**
   * Global navigation bar for the application
   *
   * @property {string} title - Title to display
   */
  module.exports = React.createClass({
    displayName: "NavigationBar",

    getInitialState: function() {
      return {
        /** Display shutdown modal? */
        shutdownModal: false
      };
    },
    /** Initiate shutdown of the hosting machine */
    doShutdown: function() {
      // TODO: Show activity indicator until connection has died
      // TODO: Make UI inactive until polling is successful again
      jQuery.ajax({
        type: "POST",
        url: "/api/system/shutdown"
      });
      this.setState({
        shutdownModal: false
      });
    },
    doReboot: function() {
      jQuery.ajax({
        type: "POST",
        url: "/api/system/rebot"
      });
    },
    /** Display shutdown modal to ask user to confirm shutdown */
    handleShutdown: function() {
      this.setState({
        shutdownModal: true
      });
    },
    render: function() {
      return (
        <div className="contain-to-grid fixed">
          {this.state.shutdownModal &&
            <modal onClose={function(){this.setState({shutdownModal: false});}.bind(this)}>
              <F.Row><F.Column><h1>Shut down/Reboot</h1></F.Column></F.Row>
              <F.Row><F.Column><p>Do you really want to shut down the device?</p></F.Column></F.Row>
              <F.Row><F.Column><p><strong>If you do, please make sure that you turn off your devices before confirming!</strong></p></F.Column></F.Row>
              <F.Row>
                <F.Column size={4}>
                  <F.Button onClick={this.doShutdown} size="small">Shut Down</F.Button>
                </F.Column>
                <F.Column size={4}>
                  <F.Button onClick={this.doReboot} size="small">Reboot</F.Button>
                </F.Column>
                <F.Column size={4}>
                  <F.Button onClick={this.props.onClose} size="small">Cancel</F.Button>
                </F.Column>
              </F.Row>
            </modal>}
          <nav className="top-bar" data-topbar>
            <ul className="title-area">
              <li className="name"> <h1><a href="/" title="Return to workflow list"><i className="fa fa-home" /> {this.props.title}</a></h1> </li>
              <li className="toggle-topbar"><a className="fa fa-list"></a></li>
            </ul>
            <section className="top-bar-section">
              {window.config.web.mode !== 'processor' &&
              <ul className="left">
                <li><a href="/workflow/new"><i className="fa fa-plus"></i> New workflow</a></li>
              </ul>}
              <ul className="right">
                <li>
                  <a href="/logging">
                    <i className="fa fa-list"></i> Show log
                    {this.props.numUnreadErrors > 0 && <F.Label severity='alert' round={true}> {this.props.numUnreadErrors}</F.Label>}
                  </a>
                </li>
                {/* Only show shutdown button if the application is running in standalone mode */}
                {window.config.web.standalone_device &&
                  (<li><a onClick={this.handleShutdown}><i className="fa fa-power-off"></i> Shut down</a></li>)}
              </ul>
            </section>
          </nav>
        </div>
      );
    }
  });
}());

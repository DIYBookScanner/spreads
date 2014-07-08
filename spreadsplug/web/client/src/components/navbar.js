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
      fnLabel = require('./foundation.js').label,
      row = require('./foundation.js').row,
      column = require('./foundation.js').column,
      fnButton = require('./foundation.js').button;

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
              <row><column><h1>Shut down/Reboot</h1></column></row>
              <row><column><p>Do you really want to shut down the device?</p></column></row>
              <row><column><p><strong>If you do, please make sure that you turn off your devices before confirming!</strong></p></column></row>
              <row>
                <column size="4">
                  <fnButton callback={this.doShutdown} size="small">Shut Down</fnButton>
                </column>
                <column size="4">
                  <fnButton callback={this.doReboot} size="small">Reboot</fnButton>
                </column>
                <column size="4">
                  <fnButton callback={this.props.onClose} size="small">Cancel</fnButton>
                </column>
              </row>
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
                    {this.props.numUnreadErrors > 0 &&<fnLabel level='alert' round={true}> {this.props.numUnreadErrors}</fnLabel>}
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

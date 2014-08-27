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
      _ = require('underscore'),
      jQuery = require('jquery'),
      F = require('./foundation.js'),
      LayeredComponentMixin = require('./overlays.js').LayeredComponentMixin;

  var ShutdownModal = React.createClass({
    mixins: [LayeredComponentMixin],

    getInitialState: function() {
      return {
        errorParams: {}
      }
    },

    /** Initiate shutdown of the hosting machine */
    doShutdown: function() {
      jQuery.ajax({
          type: "POST",
          url: "/api/system/shutdown"
      }).fail(function(xhr, textStatus) {
        if (textStatus === 'timeout') return;
        this.setState({errorParams: {title: "Could not shut down",
                                     text: xhr.responseJSON.data.message}});
      }.bind(this));
    },

    doReboot: function() {
      jQuery.ajax({
        type: "POST",
        url: "/api/system/reboot"
      }).fail(function(xhr, textStatus) {
        if (textStatus === 'timeout') return;
        this.setState({errorParams: {title: "Could not reboot",
                                     text: xhr.responseJSON.data.message}});
      }.bind(this));
    },

    render: function() {
      return (
        <F.Modal onClose={this.props.onClose}>
          <F.Row><F.Column><h1>Shutdown/Reboot</h1></F.Column></F.Row>
          <F.Row><F.Column><p>Do you really want to shut down the device?</p></F.Column></F.Row>
          <F.Row><F.Column><p><strong>If you do, please make sure that you turn off your devices before confirming!</strong></p></F.Column></F.Row>
          <F.Row>
            <F.Column size={6}>
              <F.Button onClick={this.doShutdown} size="small"><i className="fa fa-power-off" /> Shutdown</F.Button>
            </F.Column>
            <F.Column size={6}>
              <F.Button onClick={this.doReboot} size="small"><i className="fa fa-refresh" /> Reboot</F.Button>
            </F.Column>
          </F.Row>
        </F.Modal>
      );
    },

    renderLayer: function() {
      if (_.isEmpty(this.state.errorParams)) return;
      return (
        <F.Modal onClose={function(){this.setState({errorParams: {}})}.bind(this)}>
          <h2>{this.state.errorParams.title}</h2>
          <p>{this.state.errorParams.text}</p>
        </F.Modal>);
    }
  });


  var AboutModal = React.createClass({
    render: function() {
      var logoUrl = require('../../../../../doc/_static/logo.png');

      return (
        <F.Modal small={false} onClose={this.props.onClose}>
          <F.Row>
            <F.Column>
              <img src={logoUrl} className="about-logo" />
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column>
              <p>Version {window.spreadsVersion}</p>
              <p>Licensed under the terms of the <a data-bypass={true} href="https://github.com/DIYBookScanner/spreads/blob/master/LICENSE.txt">GNU Affero General Public License 3.0</a>.</p>
              <p>&copy; 2013-2014 Johannes Baiter <a data-bypass={true} href="mailto:johannes.baiter@gmail.com">&lt;johannes.baiter@gmail.com&gt;</a></p>
              <p>For a full list of contributors, please consult <a data-bypass={true} href="https://github.com/DIYBookScanner/spreads/graphs/contributors">GitHub</a></p>
            </F.Column>
          </F.Row>
        </F.Modal>);
    }
  });


  /**
   * Global navigation bar for the application
   *
   * @property {string} title - Title to display
   */
  module.exports = React.createClass({
    displayName: "NavigationBar",

    mixins: [LayeredComponentMixin],

    getInitialState: function() {
      return {
        /** Display shutdown modal? */
        shutdownModal: false,
        aboutModal: false
      };
    },

    componentWillMount: function() {
      this.bindOnDisconnect();
    },

    componentWillUnmount: function() {
      delete window.router.events.websocket.onclose;
    },

    bindOnDisconnect: function() {
      window.router.events.websocket.onclose = function() {
        this.setState({isOffline: true});
        this.checkOnline();
      }.bind(this);
    },

    checkOnline: _.throttle(function() {
      jQuery.ajax({
        type: "HEAD",
        url: "/",
        success: function() {
          this.setState({isOffline: false});
          window.router.events.connect();
          this.bindOnDisconnect();
        }.bind(this),
        error: this.checkOnline
      });
    }, 5000),

    closeShutdownModal: function () {
      this.setState({
        shutdownModal: false
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
                <li><a onClick={_.partial(this.setState.bind(this), {aboutModal: true}, null)}
                       alt="About Spreads"><i className="fa fa-info-circle" /> About</a></li>
              </ul>
            </section>
          </nav>
        </div>
      );
    },

    renderLayer: function() {
      return (
        <div>
          {this.state.ShutdownModal && <ShutdownModal onClose={this.closeShutdownModal} />}
          {this.state.aboutModal &&
            <AboutModal onClose={function(){this.setState({aboutModal: false})}.bind(this)} />}
          {this.state.isOffline &&
            <div className="overlay activity">
              <div className="animation">
                <div className="bounce"></div>
                <div className="bounce"></div>
              </div>
              <p className="text">
                <strong>The server seems to be offline</strong><br/>
                Trying to reconnect...
              </p>
            </div>}
        </div>);
    }
  });
}());

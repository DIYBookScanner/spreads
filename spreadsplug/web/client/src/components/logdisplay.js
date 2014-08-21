/** @jsx React.DOM */
/* global require, module */

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
      _ = require('underscore'),
      util = require('../util.js'),
      F = require('./foundation');

  /**
   * Helper function to compare the verbosity of two log levels.
   *
   * @param {string} levelA - the level to compare
   * @param {string} levelB - the level to compare with
   */
  function isMoreVerbose(levelA, levelB) {
    var levels = {
      'DEBUG': 10,
      'INFO': 20,
      'WARNING': 30,
      'ERROR': 40,
      'CRITICAL': 50
    };
    return levels[levelA] < levels[levelB];
  }

  /**
   * Component that displays a detailed traceback and offers the option
   * to query GitHub for similar issues and to submit a new issue with
   * the traceback and Exception name as the title.
   */
  var BugModal = React.createClass({
    propTypes: {
      traceback: React.PropTypes.string.isRequired,
      onClose: React.PropTypes.func.isRequired
    },

    render: function() {
      var exception,
          bugreportTemplate;

      exception = this.props.traceback.split("\n").slice(-2);
      bugreportTemplate = "```\n" + this.props.traceback + "\n```";
      return (
        <F.Modal onClose={this.props.onClose}>
          <F.Row>
            <F.Column>
              <h3>This should not have happened.</h3>
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column>
              <pre className="traceback">
                {this.props.traceback}
              </pre>
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column size={6}>
              <a className="action-button"
                 data-bypass={true}
                 href={"https://github.com/DIYBookScanner/spreads/search?q=" +
                       exception + "&type=Issues"}
                  target="_blank"><i className="fa fa-search"/> Search for open issues</a>
            </F.Column>
            <F.Column size={6}>
              <a className="action-button"
                 data-bypass={true}
                  href={"https://github.com/DIYBookScanner/spreads/issues/new" +
                        "?title=" + encodeURIComponent(exception) +
                        "&body=" + encodeURIComponent(bugreportTemplate) }
                  target="_blank"><i className="fa fa-github"/> Open new issue</a>
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column size={6} offset={6}>
              <a data-bypass={true} href="http://github.com/join" target="_blank">Don't have an account?</a>
            </F.Column>
          </F.Row>
        </F.Modal>
      );
    }
  });


  /**
   * Display a log entry in a table row
   */
  var LogRecord = React.createClass({
    propTypes: {
      traceback: React.PropTypes.string,
      level: React.PropTypes.string,
      origin: React.PropTypes.string.isRequired,
      message: React.PropTypes.string.isRequired,
      time: React.PropTypes.instanceOf(Date).isRequired
    },

    getInitialState: function() {
      return {
        /** Display traceback modal overlay for this entry? */
        displayBugModal: false,
      };
    },
    /**
     * Toggle display of traceback modal.
     */
    toggleBugModal: function() {
      this.setState({displayBugModal: !this.state.displayBugModal});
    },
    render: function() {
      var isSmall = util.isSmall();
      return (
        <tr className={"logentry " + (this.props.traceback ? "exception" : this.props.level)}
            onClick={this.props.traceback ? this.toggleBugModal : function(){}}>
          {!isSmall && <td className="origin">{this.props.origin}</td>}
          <td className="message">
            {this.props.traceback && <i className="fi-skull"/>}
            {" "}{this.props.message}
          </td>
          {!isSmall && <td className="time right">{this.props.time.toLocaleTimeString()}</td>}
          {this.state.displayBugModal &&
            <BugModal traceback={this.props.traceback}
                      message={this.props.message}
                      onClose={this.toggleBugModal} />
          }
        </tr>
      );
    }
  });


  /**
   * Display log entries in a table
   */
  var LogDisplay = React.createClass({
    /**
     * Load log mesages from server
     */
    loadMessages: function() {
      jQuery.ajax({
        url: "/api/log",
        data: {
          'level': this.state.loglevel,
          'start': this.state.msgStart,
          'count': this.state.msgCount
        },
        success: function(data) {
          this.setState({
            messages: data.messages,
            totalMessages: data.total_num
          });
        }.bind(this),
        dataType: "json"
      });
    },
    getInitialState: function() {
      return {
        /** Only display records with this level or higher */
        loglevel: 'info',
        /** Log messages to display */
        messages: [],
        /** Index of first log message to display */
        msgStart: 0,
        /** Number of log messages to display */
        msgCount: 25,
        /** Total number of log messages */
        totalMessages: 0
      };
    },
    /**
     * Load initial messages and start polling for updates.
     */
    componentWillMount: function() {
      this.loadMessages();
      // Initialize polling
      window.router.events.on('logrecord', function(message) {
        if (!this.isMounted()) {
          return;
        }
        if (!isMoreVerbose(message.level, this.state.loglevel)) {
          this.setState({
            messages: [message].concat(this.state.messages)
                              .slice(0, this.state.msgCount),
            totalMessages: this.state.totalMessages + 1
          });
        }
      }, this);
    },
    componentWillUnmount: function() {
      window.router.events.off('logrecord', null, this);
    },
    /** Callback when loglevel filter is changed */
    handleSetLevel: function(event) {
      this.setState({loglevel: event.target.value}, this.loadMessages);
    },
    /** Callback when page was changed */
    handleChangePage: function(pageIdx) {
      this.setState({
        msgStart: (pageIdx-1)*this.state.msgCount
      }, this.loadMessages);
    },
    /** Callback when number of log records to display was changed */
    handleSetCount: function(event) {
      this.setState({
        msgCount: event.target.value
      }, this.loadMessages);
    },
    render: function() {
      var isSmall = util.isSmall();
      var levelLabel = (
        <label htmlFor="loglevel" className={isSmall ? "": "right inline"}>
          Loglevel
        </label>);
      var numLabel = (
        <label htmlFor="msgCount" className={isSmall ? "": "right inline"}>
          # per page
        </label>);
      return (
        <main>
          <F.Row>
            <F.Column>
              <h1>Application Log</h1>
            </F.Column>
          </F.Row>
          <F.Row>
            {!isSmall && <F.Column size={2}>{levelLabel}</F.Column>}
            <F.Column size={[4, 2]}>
              {isSmall && levelLabel}
              <select id="loglevel" defaultValue="info" onChange={this.handleSetLevel}>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
                <option value="debug">Debug</option>
              </select>
            </F.Column>
            {!isSmall && <F.Column size={2}>{numLabel}</F.Column>}
            <F.Column size={[4, 2]}>
              {isSmall && numLabel}
              <select id="msgCount" defaultValue="25" onChange={this.handleSetCount}>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </F.Column>
            <F.Column size={[4, 2]}>
              <a className="action-button small download-btn" title="Download log"
                 data-bypass={true} href={"/log?level=debug&count=100"}
                 download="spreadslog.json"><i className="fa fa-download" /></a>
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column>
              <table className="logtable">
                <thead>
                  <tr>
                    {!isSmall && <th className="logger-col">Logger</th>}
                    <th className="msg-col">Message</th>
                    {!isSmall && <th className="time-col">Time</th>}
                  </tr>
                </thead>
                <tbody>
                {this.state.messages.map(function(msg, idx) {
                  return <LogRecord time={new Date(msg.time)} level={msg.level.toLowerCase()}
                                    origin={msg.origin} key={'record-'+idx}
                                    message={msg.message} traceback={msg.traceback} />;
                })}
                </tbody>
              </table>
              {(this.state.totalMessages > this.state.msgCount) &&
                <F.Pagination centered={true}
                              pageCount={Math.ceil(this.state.totalMessages/this.state.msgCount)}
                              onBrowse={this.handleChangePage} />
              }
            </F.Column>
          </F.Row>
        </main>
      );
    }
  });

  module.exports = LogDisplay;
}());

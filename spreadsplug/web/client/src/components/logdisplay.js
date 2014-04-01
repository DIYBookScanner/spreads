/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';

  var React = require('react/addons'),
      jQuery = require('jquery'),
      _ = require('underscore'),
      foundation = require('./foundation'),
      events = require('../events'),
      column = foundation.column,
      row = foundation.row,
      pagination = foundation.pagination,
      fnButton = foundation.button,
      modal = foundation.modal,
      LogRecord, BugModal;

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
   *
   * @property {string} traceback - The traceback for the exception
   * @property {function} onClose - Callback function when modal is closed
   */
  BugModal = React.createClass({
    render: function() {
      var exception,
          bugreportTemplate;

      exception = this.props.traceback.split("\n").slice(-2);
      bugreportTemplate = "```\n" + this.props.traceback + "\n```";
      return (
        <modal onClose={this.props.onClose}>
          <row>
            <column>
              <h3>This should not have happened.</h3>
            </column>
          </row>
          <row>
            <column>
              <pre className="traceback">
                {this.props.traceback}
              </pre>
            </column>
          </row>
          <row>
            <column size="6">
              <a className="action-button fi-magnifying-glass"
                  href={"https://github.com/DIYBookScanner/spreads/search?q=" +
                        exception + "&type=Issues"}
                  target="_blank"> Search for open issues</a>
            </column>
            <column size="6">
              <a className="action-button fi-social-github"
                  href={"https://github.com/DIYBookScanner/spreads/issues/new" +
                        "?title=" + encodeURIComponent(exception) +
                        "&body=" + encodeURIComponent(bugreportTemplate) }
                  target="_blank"> Open new issue</a>
            </column>
          </row>
          <row>
            <column size="6" offset="6">
              <a href="http://github.com/join" target="_blank">Don't have an account?</a>
            </column>
          </row>
        </modal>
      );
    }
  });

  /**
   * Display a log entry in a table row
   *
   * @property {string} level - Loglevel of entry
   * @property {string} origin - Origin logger
   * @property {string} message - Logging message
   * @property {Date} time - Time of entry
   * @property {string} [traceback] - Traceback of exception
   */
  LogRecord = React.createClass({
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
      return (
        <tr className={"logentry " + (this.props.traceback ? "exception" : this.props.level)}
            onClick={this.props.traceback ? this.toggleBugModal : function(){}}>
          <td className="origin">{this.props.origin}</td>
          <td className="message">
            {this.props.traceback && <i className="fi-skull"/>}
            {" "}{this.props.message}
          </td>
          <td className="time right">{this.props.time.toLocaleTimeString()}</td>
          {this.state.displayBugModal &&
            <BugModal traceback={this.props.traceback}
                      message={this.props.message}
                      onClose={this.toggleBugModal}/>
          }
        </tr>
      );
    }
  });

  /**
   * Display log entries in a table
   */
  module.exports = React.createClass({
    displayname: "LogDisplay",

    /**
     * Load log mesages from server
     */
    loadMessages: function() {
      jQuery.ajax({
        url: "/log",
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
      events.on('logrecord', function(message) {
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
      events.off('logrecord', null, this);
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
      return (
        <main>
          <row>
            <column size='18'>
              <h1>Application Log</h1>
            </column>
          </row>
          <row>
            <column size="2">
              <label htmlFor="loglevel" className="right inline">
                Loglevel
              </label>
            </column>
            <column size="2">
              <select id="loglevel" defaultValue="info" onChange={this.handleSetLevel}>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
                <option value="debug">Debug</option>
              </select>
            </column>
            <column size="2">
              <label htmlFor="msgCount" className="right inline">
                Number of records
              </label>
            </column>
            <column size="2">
              <select id="msgCount" defaultValue="25" onChange={this.handleSetCount}>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </column>
            <column size="2">
              <a className="action-button tiny fi-download" href={"/log?level=debug&count=100"} download="spreadslog.json"> Download log</a>
            </column>
          </row>
          <row>
            <column>
              <table className="logtable">
                <thead>
                  <tr>
                    <th className="logger-col">Logger</th>
                    <th className="msg-col">Message</th>
                    <th className="time-col">Time</th>
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
                <pagination centered={true}
                            pageCount={Math.ceil(this.state.totalMessages/this.state.msgCount)}
                            onBrowse={this.handleChangePage} />
              }
            </column>
          </row>
        </main>
      );
    }
  });
}());

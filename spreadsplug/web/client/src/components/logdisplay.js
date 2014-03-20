/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';

  var React = require('react/addons'),
      jQuery = require('jquery'),
      _ = require('underscore'),
      foundation = require('./foundation'),
      column = foundation.column,
      row = foundation.row,
      pagination = foundation.pagination,
      fnButton = foundation.button,
      modal = foundation.modal,
      LogRecord, BugModal;

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

  LogRecord = React.createClass({
    getInitialState: function() {
      return {
        displayBugModal: false,
        loglevel: 'info'
      };
    },
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

  module.exports = React.createClass({
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
        loglevel: 'info',
        messages: [],
        msgStart: 0,
        msgCount: 25,
        totalMessages: 0
      };
    },
    componentWillMount: function() {
      this.loadMessages();
      // Initialize polling
      (function poll() {
        jQuery.ajax({
          url: "/log",
          data: {'poll': true, 'level': this.state.loglevel},
          success: function(data) {
            this.setState({
              messages: data.messages.concat(this.state.messages)
                            .slice(0, this.state.msgCount),
              totalMessages: this.state.totalMessages += data.total_num
            });
          }.bind(this),
          dataType: "json",
          complete: function(xhr, status) {
            if (!this.isMounted()) {
              return;
            }
            else if (_.contains(["timeout", "success"], status)) {
              poll.bind(this)();
            } else {
              _.delay(poll.bind(this), 30*1000);
            }
          }.bind(this),
          timeout: 30*1000
        });
      }.bind(this)());
    },
    handleSetLevel: function(event) {
      this.setState({loglevel: event.target.value}, this.loadMessages);
    },
    handleChangePage: function(pageIdx) {
      this.setState({
        msgStart: (pageIdx-1)*this.state.msgCount
      }, this.loadMessages);
    },
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
                {this.state.messages.map(function(msg) {
                  return <LogRecord time={new Date(msg.time)} level={msg.level.toLowerCase()}
                                    origin={msg.origin}
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

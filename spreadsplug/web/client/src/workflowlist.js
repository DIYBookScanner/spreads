/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';
  var React = require('react'),
      ListItem;

  ListItem = React.createClass({
    handleRemove: function() {
    },
    handleDownload: function() {
    },
    handleContinue: function() {
    },
    render: function() {
      /* jshint ignore:start */
      var workflow = this.props.workflow;
      return (
        <li className="clearFix">
          <a href={'/workflow/' + workflow.id}>{workflow.name}</a>
          <a onClick={this.handleRemove} className="button tiny right fi-trash"></a>
          <a onClick={this.handleDownload} className="button tiny right fi-download"></a>
          <a onClick={this.handleContinue} className="button tiny right fi-play"></a>
        </li>
      );
      /* jshint ignore:end */
    }
  });

  module.exports = React.createClass({
    render: function() {
      /* jshint ignore:start */
      return (
        <ul className="no-bullet">
            {this.props.workflows.map(function(workflow) {
              return <ListItem workflow={workflow} />;
            })}
        </ul>
      );
      /* jshint ignore:end */
    }
  });
}());

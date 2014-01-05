/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';

  var React = require('react');

  module.exports = React.createClass({
    render: function() {
      var workflow = this.props.workflow;
      /* jshint ignore:start */
      return (
        <div className="workflowDetails">
          <h1>{workflow.name}</h1>

          <h2>Metadata</h2>
          <dl>
            <dt>Created</dt>
            <dd>{workflow.created.toTimeString()}</dd>

            <dt>Enabled plugins</dt>
            <dd>{workflow.config.plugins.join(', ')}</dd>

            <dt>Current step</dt>
            <dd>{workflow.current_step} {workflow.finished ? '' : <em>processing</em>}</dd>
          </dl>

          <h2>Captured images</h2>
          <ul className="small-block-grid-8">
            {workflow.images.map(function(image) {
              return (
                <li><a className="th"><img src={image + '/thumb'} /></a></li>
              );
            })}
          </ul>

          <h2>Output files</h2>
          <ul>
            {workflow.output_files.map(function(out_file) {
              return (
                <li><a href={out_file}>{out_file}</a></li>
              );
            })}
          </ul>
        </div>
      );
      /* jshint ignore:end */
    }
  });
}());

/** @jsx React.DOM */
/* global require */
(function() {
  'use strict';

  var React = require('react');

  module.exports = React.createClass({
    handleCapture: function() {
      // TODO: Implement
    },
    handleRetake: function() {
      // TODO: Implement
    },
    handleFinish: function() {
      // TODO: Implement
    },
    render: function() {
      var workflow = this.props.workflow;
      /* jshint ignore:start */
      return (
        <div className="captureDialog row">
          <ul className="small-block-grid-2">
            <li><img alt="preview odd" src={workflow.images[workflow.images.length-1]} /></li>
            <li><img alt="preview even" src={workflow.images[workflow.images.length-2]} /></li>
          </ul>
          <ul className="button-group">
            <li><a onClick={this.handleRetake} className="small button secondary"><i className="fi-refresh"></i> Retake</a></li>
            <li><a onClick={this.handleFinish} className="small button secondary"><i className="fi-check"></i> Finish</a></li>
          </ul>
          <a onClick={this.handleCapture} className="small button"><i className="fi-camera"></i> Capture</a>
        </div>
      );
      /* jshint ignore:end */
    }
  });
}());

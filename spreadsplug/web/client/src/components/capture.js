/** @jsx React.DOM */
/* global module, require, console */
(function() {
  'use strict';

  var React = require('react/addons'),
      foundation = require('./foundation.js'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      row = foundation.row,
      fnButton = foundation.button;

  module.exports = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    handleCapture: function() {
      console.log("Triggering capture");
      this.props.workflow.triggerCapture();
      // TODO: Implement
    },
    handleRetake: function() {
      console.log("Re-taking last shot");
      this.props.workflow.triggerCapture(true);
      // TODO: Implement
    },
    handleFinish: function() {
      console.log("Wrapping up capture process");
      // TODO: Implement
    },
    render: function() {
      var workflow = this.props.workflow || {};
      return (
        <row>
          {workflow.has('images') ?
            <ul className="small-block-grid-2">
              <li><img src={workflow.get('images').slice(-2)[0]} /></li>
              <li><img src={workflow.get('images').slice(-2)[1]} /></li>
            </ul>:
            ''
          }
          <ul className="button-group">
            <li>
              <fnButton callback={this.handleRetake} size="small" secondary='true'>
                <i className="fi-refresh"></i> Retake
              </fnButton>
            </li>
            <li>
              <fnButton callback={this.handleFinish} size="small" secondary='true'>
                <i className="fi-check"></i> Finish
              </fnButton>
            </li>
          </ul>
          <fnButton callback={this.handleCapture} size="small">
            <i className="fi-camera"></i> Capture
          </fnButton>
        </row>
      );
    }
  });
}());

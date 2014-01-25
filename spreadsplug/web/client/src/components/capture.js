/** @jsx React.DOM */
/* global module, require, console */
(function() {
  'use strict';

  var React = require('react/addons'),
      foundation = require('./foundation.js'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      LoadingOverlay = require('./loadingoverlay.js'),
      row = foundation.row,
      column = foundation.column,
      fnButton = foundation.button;

  module.exports = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {waiting: false,
              waitMessage: undefined};
    },
    componentWillMount: function() {
      this.triggerWaiting("Please wait while the devices  are being prepared " +
                          "for capture");
      this.props.workflow.prepareCapture(this.triggerWaiting.bind(this));
    },
    componentWillUnmount: function() {
      this.props.workflow.finishCapture();
    },
    handleCapture: function() {
      console.log("Triggering capture");
      this.triggerWaiting("Please wait for the capture to finish...");
      this.props.workflow.triggerCapture(false, this.triggerWaiting.bind(this));
      // TODO: Implement
    },
    handleRetake: function() {
      console.log("Re-taking last shot");
      this.triggerWaiting("Please wait for the capture to finish...");
      this.props.workflow.triggerCapture(true, this.triggerWaiting.bind(this));
    },
    handleFinish: function() {
      console.log("Wrapping up capture process");
      // TODO: Implement
    },
    triggerWaiting: function(message) {
      if (!this.state.waiting) {
        this.setState({
          waiting: true,
          waitMessage: message || ''
        });
      } else {
        this.setState({waiting: false});
      }
    },
    render: function() {
      var workflow = this.props.workflow || {},
          // Quick and dirty: (vpsize-(0.1*vpsize))/2
          preview_width = (document.width-(0.1*document.width))/2,
          speed;

      if (workflow && workflow.has('capture_start')) {
        var elapsed = (new Date().getTime()/1000) - workflow.get('capture_start');
        speed = (3600/elapsed)*workflow.get('images').length;
      }

      return (
        <row>
          {this.state.waiting ? <LoadingOverlay message={this.state.waitMessage} />:''}
          {workflow.has('images') ?
          <row>
            <column>
              <ul className="small-block-grid-2">
                {/* TODO: Rotate via CSS3 transform according to EXIF orientation */}
                <li><img src={workflow.get('images').slice(-2)[0]+"?width="+preview_width} /></li>
                <li><img src={workflow.get('images').slice(-2)[1]+"?width="+preview_width} /></li>
              </ul>
            </column>
          </row>:''
          }
          <row>
            <column>
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
            </column>
          </row>
          <row>
            <column>
              <fnButton callback={this.handleCapture} size="small">
                <i className="fi-camera"></i> Capture
              </fnButton>
            </column>
          </row>
          <row>
            <column size="6">
              {workflow.get('images').length + ' images'}
            </column>
            <column size="6">
              {speed ? 'Average speed: ' + speed + ' pages/hour' : ''}
            </column>
          </row>
        </row>
      );
    }
  });
}());

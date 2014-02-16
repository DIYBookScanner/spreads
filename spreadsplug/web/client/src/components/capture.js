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
          speed;
      if (workflow && workflow.has('capture_start')) {
        var elapsed = (new Date().getTime()/1000) - workflow.get('capture_start');
        speed = (3600/elapsed)*workflow.get('images').length | 0;
      }

      return (
        <div>
          {this.state.waiting ? <LoadingOverlay message={this.state.waitMessage} />:''}
          {workflow.has('images') && workflow.get('images').length ?
          <row>
            <column>
              {/* TODO: If there isn't another trigger within 5 seconds, load
               /*       a higher resolution previoew. */}
              <ul className="show-for-landscape small-block-grid-2 capture-preview">
                <li><img src={workflow.get('images').slice(-2)[0]+"/thumb"} /></li>
                <li><img src={workflow.get('images').slice(-2)[1]+"/thumb"} /></li>
              </ul>
              <ul className="show-for-portrait small-block-grid-1 medium-block-grid-2 capture-preview">
                <li><img src={workflow.get('images').slice(-2)[0]+"/thumb"} /></li>
                <li><img src={workflow.get('images').slice(-2)[1]+"/thumb"} /></li>
              </ul>
            </column>
          </row>:''
          }
          <row className="capture-info">
            <column size="6">
              <span className="pagecount">{workflow.get('images').length} pages</span>
            </column>
            {speed ? 
            <column size="6">
              <span className="capturespeed">{speed} pages/hour</span>
            </column>:''}
          </row>
          <row>
            <div className="small-12 capture-controls columns">
              <ul>
                <li>
                  <fnButton callback={this.handleRetake} secondary='true' size='large'>
                      <i className="fi-refresh"></i>
                  </fnButton>
                </li>
                <li id="trigger-capture">
                  <fnButton callback={this.handleCapture} size='large'>
                    <i className="fi-camera"></i>
                  </fnButton>
                </li>
                <li>
                  <fnButton callback={this.handleFinish} secondary='true' size='large'>
                      <i className="fi-check"></i>
                  </fnButton>
                </li>
              </ul>
            </div>
          </row>
        </div>
      );
    }
  });
})();

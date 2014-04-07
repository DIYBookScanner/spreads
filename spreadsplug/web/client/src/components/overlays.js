/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      Activity, LightBox, Progress;

  /**
   * Display an overlay with a CSS3 animation indicating ongoing activty.
   *
   * @property {string} message - Message to display below the activity
   *    animation
   */
  Activity = React.createClass({
    render: function() {
      return (
        <div className="overlay activity">
          <div className="animation">
            <div className="bounce"></div>
            <div className="bounce"></div>
          </div>
          <p className="text">{this.props.message}</p>
        </div>
      );
    }
  });

  /**
   * Display image in lightbox overlay.
   *
   * @property {function} onClose - Callback function for when the lightbox is closed.
   * @property {url} src - Source URL for the image to be displayed
   */
  LightBox = React.createClass({
    render: function() {
      return (
        <div onClick={this.props.onClose} className="overlay lightbox">
          <a href={this.props.src} target='_blank'>
            <img src={this.props.src} />
          </a>
        </div>
      );
    }
  });

  Progress = React.createClass({
      render: function() {
        var widthPercent;
        if (this.props.progress > 1) widthPercent = this.props.progress | 0;
        else widthPercent = (this.props.progress*100) | 0;
        return (
          <div className="overlay spreads-progress">
            <div className="progress">
              <span className="meter" style={{width: widthPercent+"%"}}></span>
              <span className="status">{this.props.statusMessage}</span>
            </div>
          </div>
        );
      }
  });

  module.exports = {
      Activity: Activity,
      LightBox: LightBox,
      Progress: Progress
  }
}());

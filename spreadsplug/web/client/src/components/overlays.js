/** @jsx React.DOM */
/* global module, require */

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
      _ = require('underscore');

  /** Create a new "layer" on the page like a modal or overlay
   *
   * MIT License, (c) 2014 Khan Academy
   * https://github.com/Khan/react-components
   */
  var LayeredComponentMixin = {
    componentDidMount: function() {
      // Appending to the body is easier than managing the z-index of
      // everything on the page. It's also better for accessibility and
      // makes stacking a snap (since components will stack in mount order).
      this._renderLayer();
    },

    componentDidUpdate: function() {
      this._renderLayer();
    },

    componentWillUnmount: function() {
      if (!this._layer) return;
      this._unrenderLayer();
    },

    _renderLayer: function() {
      var component = this.renderLayer();

      if (!component && this._layer) {
        this._unrenderLayer()
        return;
      }

      if (!component) {
        return;
      }

      if (!this._layer) {
        this._layer = document.createElement('div');
        document.body.appendChild(this._layer);
      }

      // By calling this method in componentDidMount() and
      // componentDidUpdate(), you're effectively creating a "wormhole" that
      // funnels React's hierarchical updates through to a DOM node on an
      // entirely different part of the page.
      React.renderComponent(component, this._layer);

      if (this.layerDidMount) {
        this.layerDidMount(this._layer);
      }
    },

    _unrenderLayer: function() {
      if (this.layerWillUnmount) {
        this.layerWillUnmount(this._layer);
      }
      React.unmountComponentAtNode(this._layer);
      document.body.removeChild(this._layer);
      this._layer = null;
    }
  };

  var Overlay = React.createClass({
    propTypes: {
      color: React.PropTypes.string
    },
    getDefaultProps: function() {
      return {
        color: 'rgba(0, 0, 0, 0.8)'
      }
    },
    render: function() {
      var classes = "overlay";
      var styles = {
        background: this.props.color
      }
      if (this.props.className) {
        classes = [classes, this.props.className].join(" ");
      }
      return (
        <div className={classes} style={styles}>
          {this.props.children}
        </div>);
    }
  });

  /**
   * Display an overlay with a CSS3 animation indicating ongoing activty.
   *
   * @property {string} message - Message to display below the activity
   *    animation
   */
  var Activity = React.createClass({
    displayName: "ActivityOverlay",
    render: function() {
      return (
        <div className="activity">
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
  var LightBox = React.createClass({
    displayName: "LightBox",
    propTypes: {
      imageUrl: React.PropTypes.string.isRequired,
      sequenceNumber: React.PropTypes.number,
      sequenceLength: React.PropTypes.number,
      onBrowse: React.PropTypes.func,
      onClose: React.PropTypes.func
    },
    getDefaultProps: function() {
      return {
        sequenceNumber: 0,
        sequenceLength: Infinity
      }
    },
    getInitialState: function() {
      return {};
    },
    handleResize: function(e) {
      // TODO: Shouldn't this be possible just with CSS?
      var imgNode = this.refs.image.getDOMNode();
      this.setState({
          controlY: imgNode.offsetTop,
          controlHeight: imgNode.offsetHeight,
          previousX: imgNode.offsetLeft-80,
          nextX: imgNode.offsetLeft + imgNode.offsetWidth
      });
    },
    handleNext: function(e) {
      e.stopPropagation();
      this.props.onBrowse(this.props.sequenceNumber + 1);
    },
    handlePrevious: function(e) {
      e.stopPropagation();
      this.props.onBrowse(this.props.sequenceNumber - 1);
    },
    componentDidMount: function() {
      window.addEventListener("resize", this.handleResize);
    },
    componentWillUnmount: function() {
      window.removeEventListener("resize", this.handleResize);
    },
    render: function() {
      var hasPrevious = this.props.sequenceNumber > 0;
      var hasNext = this.props.sequenceNumber < this.props.sequenceLength-1;
      return (
        <div title="Close lightbox" onClick={this.props.onClose} className="overlay lightbox">
          <a data-bypass={true} title="Open full resolution image in new tab"
             className="open-image" href={this.props.imageUrl} target='_blank'>
            <img ref="image" className={this.props.sequenceNumber % 2 ? 'odd' : 'even'}
                 src={this.props.imageUrl} onLoad={this.handleResize}/>
          </a>
          {(this.state.previousX !== undefined) && this.props.onBrowse && hasPrevious &&
            <a title="View previous page" className="control"
                style={{position: 'fixed',
                        left: this.state.previousX,
                        width: 80,
                        height: this.state.controlHeight,
                        'line-height': this.state.controlHeight,
                        top: this.state.controlY}}
                        onClick={this.handlePrevious} >
              <i className="fa fa-caret-left fa-5x" />
            </a>
          }
          {(this.state.nextX !== undefined) && this.props.onBrowse && hasNext &&
            <a title="View next page" className="control"
                style={{position: 'fixed',
                        left: this.state.nextX,
                        width: 80,
                        height: this.state.controlHeight,
                        'line-height': this.state.controlHeight,
                        top: this.state.controlY}}
                        onClick={this.handleNext} >
              <i className="fa fa-caret-right fa-5x" />
            </a>
          }
        </div>
      );
    }
  });

  var Progress = React.createClass({
    displayName: "ProgressOverlay",
    render: function() {
      var widthPercent;
      if (this.props.progress > 1) widthPercent = this.props.progress | 0;
      else widthPercent = (this.props.progress*100) | 0;
      return (
        <div className="progress">
          <span className="meter" style={{width: widthPercent+"%"}}></span>
          <span className="status">{this.props.statusMessage}</span>
        </div>
      );
    }
  });

  module.exports = {
    Overlay: Overlay,
    Activity: Activity,
    LightBox: LightBox,
    Progress: Progress,
    LayeredComponentMixin: LayeredComponentMixin
  }
}());

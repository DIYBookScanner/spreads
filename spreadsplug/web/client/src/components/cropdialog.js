/** @jsx React.DOM */
/* global module, require, console */

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

  var _ = require('underscore'),
      React = require('react/addons'),
      util = require('../util.js'),
      F = require('./foundation.js');

  var CropWidget = React.createClass({
    propTypes: {
      /** Current crop parameters */
      cropParams: React.PropTypes.object,
      /** Original, unscaled width of image source */
      nativeWidth: React.PropTypes.number,
      /** Original, unscaled height of image source */
      nativeHeight: React.PropTypes.number,
      /** Whether to show input boxes with values below image */
      showInputs: React.PropTypes.bool,
      /** Source image URL */
      imageSrc: React.PropTypes.string,
      /** Function that is called when the user decides to save the crop
       * selection */
      onSave: React.PropTypes.func
    },

    getInitialState: function() {
      return {
        initialX: 0,
        initialY: 0,
        dragOrigin: null,
        cropParams: this.props.cropParams,
        imageSize: {}
      };
    },

    getDefaultProps: function() {
      return {
        showInputs: false,
        cropParams: {}
      };
    },

    componentDidMount: function() {
      window.addEventListener("resize", this.handleResize);
    },

    componentWillUnmount: function() {
      window.removeEventListener("resize", this.handleResize);
    },

    handleTouchStart: function(e) {
      e.preventDefault();
      var touch = e.targetTouches[0],
          dragOrigin = e.target.className.split(' ')[0];
      document.addEventListener('touchmove', this.handleTouchMove);
      document.addEventListener('touchend', this.handleTouchEnd);
      this.setState({
        initialX: touch.clientX,
        initialY: touch.clientY,
        dragOrigin: dragOrigin
      });
    },

    handleMouseDown: function(e) {
      e.preventDefault();
      var dragOrigin = e.target.className.split(' ')[0];
      document.addEventListener('mousemove', this.handleMouseMove);
      document.addEventListener('mouseup', this.handleMouseUp);
      this.setState({
        initialX: e.clientX,
        initialY: e.clientY,
        dragOrigin: dragOrigin
      });
    },

    handleMouseMove: function(e) {
      e.preventDefault();
      var offsetX = e.clientX - this.state.initialX,
          offsetY = e.clientY - this.state.initialY,
          origin = this.state.dragOrigin,
          factor = this.state.imageSize.width / this.state.imageSize.nativeWidth,
          params;
      params = this.handleBoxResize(Math.ceil(offsetX/factor),
                                    Math.ceil(offsetY/factor),
                                    origin);
      this.setState({
        initialX: e.clientX,
        initialY: e.clientY,
        cropParams: params
      });
    },

    handleTouchMove: function(e) {
      e.preventDefault();
      var touch = e.targetTouches[0],
          offsetX = touch.clientX - this.state.initialX,
          offsetY = touch.clientY - this.state.initialY,
          origin = this.state.dragOrigin,
          factor = this.state.imageSize.width / this.state.imageSize.nativeWidth,
          params;
      params = this.handleBoxResize(Math.ceil(offsetX/factor),
                                    Math.ceil(offsetY/factor),
                                    origin);
      this.setState({
        initialX: touch.clientX,
        initialY: touch.clientY,
        cropParams: params
      });
    },

    handleMouseUp: function(e) {
      e.preventDefault();
      document.removeEventListener('mousemove', this.handleMouseMove);
      document.removeEventListener('mouseup', this.handleMouseUp);
      this.setState({dragOrigin: undefined});
    },

    handleTouchEnd: function(e) {
      e.preventDefault();
      document.removeEventListener('touchmove', this.handleTouchMove);
      document.removeEventListener('touchend', this.handleTouchEnd);
      this.setState({dragOrigin: undefined});
    },

    handleBoxResize: function(offsetX, offsetY, origin) {
      var newParams = _.clone(this.state.cropParams),
          imgSize = this.state.imageSize,
          factor = imgSize.width / imgSize.nativeWidth;

      function roundTo(num, factor) {
        if (num > 0) {
          return Math.ceil(num/factor)*factor;
        } else if (num < 0) {
          return Math.floor(num/factor)*factor;
        } else {
          return num;
        }
      }

      // Ensure that both offsets are multiples of 8
      offsetX = roundTo(offsetX, 8);
      offsetY = roundTo(offsetY, 8);

      // Calculate new top ofset
      if (origin === "cropbox" || origin.split("-")[0] === "upper") {
        var minTop = Math.ceil(imgSize.top/factor),
            newTop = newParams.top + offsetY;
        if (newTop < minTop) newTop = minTop;
        if (newTop > imgSize.nativeHeight) newTop = imgSize.nativeHeight;
        newParams.top = newTop;
      }

      // Calculate new left offset
      if (origin === "cropbox" || origin.split("-")[1] == "left") {
        var minLeft = Math.ceil(imgSize.left/factor),
            newLeft = newParams.left + offsetX;
        if (newLeft < minLeft) newLeft = minLeft;
        if (newLeft > imgSize.nativeWidth) newLeft = imgSize.nativeWidth;
        newParams.left = newLeft;
      }

      // Calculate new height
      if (origin.split("-")[0] === "upper") {
        newParams.height -= offsetY;
      } else if (origin.split("-")[0] === "lower") {
        newParams.height += offsetY;
      }

      // Calculate new width
      if (origin.split("-")[1] === 'left') {
        newParams.width -= offsetX;
      } else if (origin.split("-")[1] === 'right') {
        newParams.width += offsetX;
      }

      // Check horizontal constraints
      if ((newParams.left + newParams.width) > imgSize.nativeWidth) {
        newParams.width = this.state.cropParams.width;
        newParams.left = this.state.cropParams.left;
      }

      // Check vertical constraints
      if ((newParams.top + newParams.height) > imgSize.nativeHeight) {
        newParams.top = this.state.cropParams.top;
        newParams.height = this.state.cropParams.height;
      }

      return newParams;
    },

    handleLoad: function(e) {
      var newState = {
        imageSize: this.getImageSize()
      };
      if (_.isEmpty(this.state.cropParams)) {
        newState.cropParams = {
          top: 0,
          left: 0,
          width: newState.imageSize.nativeWidth,
          height: newState.imageSize.nativeHeight
        };
      }
      this.setState(newState);
    },

    getImageSize: function() {
      var imgNode = this.refs.image.getDOMNode();
      return {
        top: imgNode.offsetTop,
        left: imgNode.offsetLeft,
        width: imgNode.offsetWidth,
        height: imgNode.offsetHeight,
        nativeWidth: this.props.nativeWidth || imgNode.naturalWidth,
        nativeHeight: this.props.nativeHeight || imgNode.naturalHeight
      };
    },

    handleResize: function() {
      this.setState({
        imageSize: this.getImageSize()
      });
    },

    handleInputChange: function(e) {
      var type = e.target.name,
          newValue = e.target.value,
          cropParams = this.state.cropParams,
          offsetX = 0,
          offsetY = 0,
          origin;
      switch (type) {
        case "left":
          offsetX = newValue - cropParams.left;
          origin = "middle-left";
          break;
        case "top":
          offsetY = newValue - cropParams.top;
          origin = "upper-middle";
          break;
        case "width":
          offsetX = newValue - cropParams.width;
          origin = "middle-right";
          break;
        case "height":
          offsetY = newValue - cropParams.height;
          origin = "lower-middle";
          break;
      }
      this.setState({
        cropParams: this.handleBoxResize(offsetX, offsetY, origin)
      });
    },

    getStyle: function(cropParams) {
      if (!this.state.imageSize) return { display: "none" };
      var factor = this.state.imageSize.width / this.state.imageSize.nativeWidth;
      return {
        left: Math.ceil(cropParams.left*factor),
        top: Math.ceil(cropParams.top*factor),
        width: Math.ceil(cropParams.width*factor),
        height: Math.ceil(cropParams.height*factor)
      };
    },

    shouldComponentUpdate: function(nextProps, nextState) {
      var should = false;
      if ((nextState.imageSize != this.state.imageSize) ||
          (nextState.dragOrigin != this.state.dragOrigin)) {
        should = true;
      }
      else if (nextState.cropParams != this.state.cropParams) {
        if (this.props.showInputs) {
          should = true;
        } else {
          var newStyle = this.getStyle(nextState.cropParams),
              oldStyle = this.getStyle(this.state.cropParams);
          should = (newStyle != oldStyle);
        }
      }
      return should;
    },

    handleSubmit: function(e) {
      e.preventDefault();
      if (this.props.onSave) {
        var params = _.clone(this.state.cropParams);
        params.nativeWidth = this.state.imageSize.nativeWidth;
        params.nativeHeight = this.state.imageSize.nativeHeight;
        this.props.onSave(params);
      }
    },

    render: function() {
      var dragCorners = ["upper-left", "upper-middle", "upper-right", "middle-left",
                        "middle-right", "lower-left", "lower-middle", "lower-right"],
          hasTouch = util.isTouchDevice(),
          cx = React.addons.classSet,
          cropClasses;
      cropClasses = cx({
        'cropbox': true,
        'active': this.state.dragOrigin === 'cropbox',
        'touch': hasTouch
      });
      return (
        <div>
        <div className="crop-container">
          <div ref="box"
               className={cropClasses}
               onMouseDown={(!hasTouch) && this.handleMouseDown}
               onTouchStart={hasTouch && this.handleTouchStart}
               style={this.getStyle(this.state.cropParams)}>
            {dragCorners.map(function(pos) {
              var classes = {};
              classes[pos] = true;
              classes["drag"] = true;
              classes["active"] = (pos === this.state.dragOrigin);
              classes["touch"] = hasTouch;
              return <div key={pos} ref={pos} className={cx(classes)}
                          onMouseDown={(!hasTouch) && this.handleMouseDown}
                          onTouchStart={hasTouch && this.handleTouchStart} />;
            }, this)}
          </div>
          <img src={this.props.imageSrc} ref="image" onLoad={this.handleLoad} />
        </div>
        <form onSubmit={this.handleSubmit}>
          {this.props.showInputs && this.state.cropParams &&
            <F.Row>
              {_.map(["left", "top", "width", "height"], function(param) {
                return(
                  <F.Column  key={"input-" + param} size={[6, 3]}>
                    <label>{util.capitalize(param)}
                      <input type="number"
                            name={param} value={this.state.cropParams[param]}
                            onChange={this.handleInputChange}/>
                    </label>
                  </F.Column>
                );}, this)}
            </F.Row>
          }
          <F.Button className={"action-button small"}
                    onClick={this.handleSubmit}>
            <i className="fa fa-save" /> Save
          </F.Button>
        </form>
      </div>);
    }
  });

  module.exports = CropWidget;
}());

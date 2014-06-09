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
      jQuery = require('jquery'),
      _ = require('underscore'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      foundation = require('./foundation.js'),
      lightbox = require('./overlays.js').LightBox,
      isTouchDevice = require('../util.js').isTouchDevice,
      row = foundation.row,
      column = foundation.column,
      pagination = foundation.pagination,
      PagePreview;

  PagePreview = React.createClass({
    displayName: "PagePreview",
    getInitialState: function() {
      // We always display the toolbar when we're on a touch device, since
      // hover events are not available.
      return { displayToolbar: isTouchDevice() };
    },
    toggleToolbar: function() {
      if (!isTouchDevice()) {
        this.setState({displayToolbar: !this.state.displayToolbar});
      }
    },
    render: function() {
      var cx = require('react/addons').addons.classSet,
          liClasses = cx({
            'th': true,
            'page-preview': true,
            'selected': this.props.selected
          });
      return (
        <li className={liClasses} title="Open full resolution image in lightbox"
            onMouseEnter={this.toggleToolbar} onMouseLeave={this.toggleToolbar}>
          <a onClick={this.props.selectCallback}
             title={this.props.selected ? "Deselect image" : "Select image"}>
            <img src={this.props.image + '/thumb'} />
          </a>
          {this.state.displayToolbar &&
          <a onClick={this.props.lightboxCallback}  className="toggle-zoom fi-zoom-in" />}
        </li>);
    }
  })

  /**
   * Component that displays details for a single workflow along with
   * a paginated grid of thumbnail images and a list of generated output
   * files.
   *
   * @property {Workflow} workflow - Workflow to display
   */
  module.exports = React.createClass({
    displayName: "WorkflowDisplay",

    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin],

    /** Activates databinding for `workflow` model property. */
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {
        /** Index number of first thumbnail picture */
        thumbStart: 0,
        /** Number of thumbnails to display */
        thumbCount: 24,
        /** Image to display in a lightobx overlay */
        lightboxImage: undefined,
        selectedImages: []
      };
    },
    /**
     * Toggle display of image lightbox.
     *
     * If no `img` parameter is passed, the lightbox will be disabled,
     * otherwise it will be enabled with the `img` as its content.
     *
     * @param {string} [img] - URL for image to be displayed in lightbox
     */
    toggleLightbox: function(img) {
      this.setState({
        lightboxImage: img
      });
    },
    /**
     * Change page of page thumbnail display.
     *
     * @param {number} pageIdx - Page number to chagne to
     */
    browse: function(pageIdx) {
      this.setState({
        thumbStart: (pageIdx-1)*this.state.thumbCount
      });
    },
    toggleImageSelect: function(img) {
      var images = this.state.selectedImages;
      if (_.contains(images, img)) {
        this.setState({selectedImages: _.without(images, img)});
      } else {
        images.push(img);
        this.setState({selectedImages: images});
      }
    },
    bulkDelete: function() {
      this.props.workflow.deleteImages(this.state.selectedImages);
    },
    render: function() {
      var workflow = this.props.workflow,
          pageCount = Math.ceil(workflow.get('raw_images').length / this.state.thumbCount),
          thumbStart = this.state.thumbStart,
          thumbStop = this.state.thumbStart+this.state.thumbCount,
          deleteClasses = require('react/addons').addons.classSet({
            'small': true,
            'button': true,
            'fi-trash': true,
            'disabled': this.state.selectedImages.length === 0
          });
      return (
        <main>
          {/* Display image in lightbox overlay? */}
          {this.state.lightboxImage &&
            <lightbox onClose={function(){this.toggleLightbox();}.bind(this)}
                      src={this.state.lightboxImage} />
          }
          <row>
            <column size='12'>
              <h1>{workflow.get('name')}</h1>
            </column>
          </row>
          <row>
            <column size='12'>
              <h2>Metadata</h2>
              <ul>
                {workflow.get('status').step ?
                  <li>{workflow.get('status').step}</li>:
                  <li>Current step: <em>inactive</em></li>
                }
                <li>Enabled plugins:{' '}{workflow.get('config').plugins.join(', ')}</li>
              </ul>
            </column>
          </row>

          {/* Only show image thumbnails when there are images in the workflow */}
          {(workflow.has('raw_images') && workflow.get('raw_images')) &&
          <row>
            <column size='12'>
              <h2>Captured images</h2>
              <div className="button-bar">
                <ul className="button-group">
                  <li><a onClick={this.bulkDelete} className={deleteClasses}> Delete</a></li>
                </ul>
              </div>
              <ul ref="imagegrid" className="small-block-grid-2 medium-block-grid-4 large-block-grid-6">
                {workflow.get('raw_images').slice(thumbStart, thumbStop).map(function(image) {
                    return (
                      <PagePreview image={image} key={image} selected={_.contains(this.state.selectedImages, image)}
                                   selectCallback={function(){this.toggleImageSelect(image)}.bind(this)}
                                   lightboxCallback={function(){this.toggleLightbox(image);}.bind(this)} />
                    );
                  }.bind(this))}
              </ul>
              {pageCount > 1 && <pagination centered={true} pageCount={pageCount} onBrowse={this.browse} />}
            </column>
          </row>}

          {/* Only show output file list if there are output files in the workflow */}
          {(workflow.has('output_files') && workflow.get('output_files').length) &&
          <row>
            <column size='12'>
              <h2>Output files</h2>
              <ul ref="outputlist">
                {workflow.get('output_files').map(function(outFile) {
                    return (
                      <li key={outFile}><a href={outFile}>{outFile}</a></li>
                    );
                  })}
              </ul>
            </column>
          </row>}
        </main>
      );
    }
  });
}());

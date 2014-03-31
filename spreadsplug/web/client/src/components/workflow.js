/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';

  var React = require('react/addons'),
      ModelMixin = require('../workflow.js'),
      foundation = require('./foundation.js'),
      lightbox = require('./overlays.js').LightBox,
      row = foundation.row,
      column = foundation.column,
      pagination = foundation.pagination;

  /**
   * Component that displays details for a single workflow along with
   * a paginated grid of thumbnail images and a list of generated output
   * files.
   *
   * @property {Workflow} workflow - Workflow to display
   */
  module.exports = React.createClass({
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
        lightboxImage: undefined
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
    render: function() {
      var workflow = this.props.workflow,
          pageCount = (workflow.get('images').length / this.state.thumbCount) | 0,
          thumbStart = this.state.thumbStart,
          thumbStop = this.state.thumbStart+this.state.thumbCount;
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
                {workflow.has('step') ?
                  <li>{workflow.get('step') + ': ' +
                       (workflow.get('step_done') ? 'completed' : 'in progress')}</li>:
                  <li>Current step: <em>inactive</em></li>
                }
                <li>Enabled plugins:{' '}{workflow.get('config').plugins.join(', ')}</li>
              </ul>
            </column>
          </row>

          {/* Only show image thumbnails when there are images in the workflow */}
          {(workflow.has('images') && workflow.get('images')) &&
          <row>
            <column size='12'>
              <h2>Captured images</h2>
              <ul className="small-block-grid-2 medium-block-grid-4 large-block-grid-6">
                {workflow.get('images').slice(thumbStart, thumbStop).map(function(image) {
                    return (
                      <li key={image}>
                        <a className="th" onClick={
                            function(){this.toggleLightbox(image);}.bind(this)}>
                          <img src={image + '/thumb'} />
                        </a>
                      </li>
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
              <ul>
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

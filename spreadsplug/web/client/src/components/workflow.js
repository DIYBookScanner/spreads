/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';

  var React = require('react/addons'),
      ModelMixin = require('../workflow.js'),
      foundation = require('./foundation.js'),
      lightbox = require('./lightbox.js'),
      row = foundation.row,
      column = foundation.column,
      pagination = foundation.pagination;

  module.exports = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {
        thumbStart: 0,
        thumbCount: 24,
        lightboxImage: undefined
      };
    },
    openLightbox: function(img) {
      this.setState({
        lightboxImage: img
      });
    },
    closeLightbox: function() {
      this.setState({
        lightboxImage: undefined
      });
    },
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
          {this.state.lightboxImage &&
            <lightbox onClose={this.closeLightbox} src={this.state.lightboxImage} />
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
          {(workflow.has('images') && workflow.get('images')) &&
          <row>
            <column size='12'>
              <h2>Captured images</h2>
              <ul className="small-block-grid-2 medium-block-grid-4 large-block-grid-6">
                {workflow.get('images').slice(thumbStart, thumbStop).map(function(image) {
                    return (
                      <li key={image}>
                        <a className="th" onClick={function(){this.openLightbox(image);}.bind(this)}>
                          <img src={image + '/thumb'} />
                        </a>
                      </li>
                    );
                  }.bind(this))}
              </ul>
              {pageCount > 1 && <pagination centered={true} pageCount={pageCount} onBrowse={this.browse} />}
            </column>
          </row>}
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

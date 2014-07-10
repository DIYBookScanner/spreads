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
      util = require('../util.js'),
      row = foundation.row,
      column = foundation.column,
      pagination = foundation.pagination,
      PagePreview;

  PagePreview = React.createClass({
    displayName: "PagePreview",
    getInitialState: function() {
      // We always display the toolbar when we're on a touch device, since
      // hover events are not available.
      return { displayToolbar: util.isTouchDevice() };
    },
    toggleToolbar: function() {
      if (!util.isTouchDevice()) {
        this.setState({displayToolbar: !this.state.displayToolbar});
      }
    },
    render: function() {
      var cx = require('react/addons').addons.classSet,
          liClasses = cx({
            'th': true,
            'page-preview': true,
            'selected': this.props.selected
          }),
          page = this.props.page,
          thumbUrl = util.getPageUrl(this.props.workflow, page, this.props.imageType, true);
      return (
        <li className={liClasses} title="Open full resolution image in lightbox"
            onMouseEnter={this.toggleToolbar} onMouseLeave={this.toggleToolbar}>
          <row>
            <column>
              <a onClick={this.props.selectCallback}
                title={this.props.selected ? "Deselect image" : "Select image"}>
                <img src={thumbUrl} />
              </a>
              {this.state.displayToolbar &&
              <a onClick={this.props.lightboxCallback}  className="toggle-zoom fa fa-search-plus" />}
            </column>
          </row>
          <row>
            <column>
              {page.page_label}
            </column>
          </row>
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
        lightboxNext: undefined,
        lightboxPrevious: undefined,
        imageType: 'raw',
        selectedPages: []
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
    toggleLightbox: function(workflow, page) {
      console.debug(workflow, page);
      var image, next, previous;
      if (page) {
        var allPages = workflow.get('pages'),
            pageIdx = allPages.indexOf(page);
        image = util.getPageUrl(this.props.workflow, page, this.state.imageType, false);
        next = (pageIdx != (allPages.length-1)) && allPages[pageIdx+1];
        previous = (pageIdx != 0) && allPages[pageIdx-1];
      }
      this.setState({
        lightboxImage: image,
        lightboxNext: next,
        lightboxPrevious: previous
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
    togglePageSelect: function(page) {
      var pages = this.state.selectedPages;
      if (_.contains(pages, page)) {
        this.setState({selectedPages: _.without(pages, page)});
      } else {
        pages.push(page);
        this.setState({selectedPages: pages});
      }
    },
    bulkDelete: function() {
      this.props.workflow.deletePages(this.state.selectedPages);
    },
    handleImageTypeSelect: function(event) {
      this.setState({
        imageType: event.target.value
      });
    },
    render: function() {
      var workflow = this.props.workflow,
          pageCount = Math.ceil(workflow.get('pages').length / this.state.thumbCount),
          thumbStart = this.state.thumbStart,
          thumbStop = this.state.thumbStart+this.state.thumbCount,
          deleteClasses = require('react/addons').addons.classSet({
            'small': true,
            'button': true,
            'disabled': this.state.selectedPages.length === 0
          }),
          imageTypes = ['raw'].concat(_.without(_.keys(workflow.get('pages')[0].processed_images), 'tesseract')),
          metadata = workflow.get('metadata');
      return (
        <main>
          {/* Display image in lightbox overlay? */}
          {this.state.lightboxImage &&
            <lightbox onClose={function(){this.toggleLightbox();}.bind(this)}
                      src={this.state.lightboxImage}
                      handleNext={this.state.lightboxNext && function(e) {
                        e.stopPropagation();
                        this.toggleLightbox(workflow, this.state.lightboxNext);
                      }.bind(this)}
                      handlePrevious={this.state.lightboxPrevious && function(e) {
                        e.stopPropagation();
                        this.toggleLightbox(workflow, this.state.lightboxPrevious);
                      }.bind(this)}/>
          }
          <row>
            <column size='12'>
              <h1>{metadata.title}</h1>
            </column>
          </row>
          <row className="metadata-view">
            <column size='12'>
              <h2>Metadata</h2>
              {_.map(window.metadataSchema, function(field) {
                if (!_.has(metadata, field.key)) return;
                var valueNode,
                    value = metadata[field.key];
                if (field.multivalued) {
                  valueNode = (
                    <ul>
                    {_.map(value, function(item) {
                      return <li key={item}>{item}</li>;
                    })}
                    </ul>);
                } else {
                  valueNode = value;
                }
                return (
                  <row key={field.key}>
                    <column size={2}>{field.description}</column>
                    <column size={10}>{valueNode}</column>
                  </row>);
                })}
            </column>
          </row>

          {/* Only show image thumbnails when there are images in the workflow */}
          {(workflow.has('pages') && workflow.get('pages')) &&
          <row>
            <column size='12'>
              <h2>Pages</h2>
              <div className="button-bar">
                <ul className="button-group">
                  <li><a onClick={this.bulkDelete} className={deleteClasses}><i className="fa fa-trash-o" /> Delete</a></li>
                  <li>
                    <select onChange={this.handleImageTypeSelect}>
                    {imageTypes.map(function(name) {
                      return <option key={name} value={name}>{name}</option>;
                    })}
                    </select>
                  </li>
                </ul>
              </div>
              <ul ref="pagegrid" className="small-block-grid-2 medium-block-grid-4 large-block-grid-6">
                {workflow.get('pages').slice(thumbStart, thumbStop).map(function(page) {
                    return (
                      <PagePreview page={page} workflow={workflow} key={page.capture_num} imageType={this.state.imageType}
                                   selected={_.contains(this.state.selectedPages, page)}
                                   selectCallback={function(){this.togglePageSelect(page)}.bind(this)}
                                   lightboxCallback={function(){this.toggleLightbox(workflow, page);}.bind(this)} />
                    );
                  }.bind(this))}
              </ul>
              {pageCount > 1 && <pagination centered={true} pageCount={pageCount} onBrowse={this.browse} />}
            </column>
          </row>}

          {/* Only show output file list if there are output files in the workflow */}
          {!_.isEmpty(workflow.get('out_files')) &&
          <row>
            <column size='12'>
              <h2>Output files</h2>
              <ul ref="outputlist" className="fa-ul">
                {_.map(workflow.get('out_files'), function(outFile) {
                    var fileUrl = '/api/workflow/' + this.props.workflow.id + '/output/' + outFile.name,
                        classes = {
                          'fa-li': true,
                          'fa': true,
                        };
                    if (outFile.mimetype === "text/html") classes['fa-file-code-o'] = true;
                    else if (outFile.mimetype === "application/pdf") classes['fa-file-pdf-o'] = true;
                    else classes['fa-file'] = true;
                    return (
                      <li key={outFile.name}><a href={fileUrl}><i className={React.addons.classSet(classes)} /> {outFile.name}</a></li>
                    );
                  }, this)}
              </ul>
            </column>
          </row>}
        </main>
      );
    }
  });
}());

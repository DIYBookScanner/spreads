/** @jsx React.DOM */
/* global require, module */

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
      _ = require('underscore'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      LoadingOverlay = require('./overlays.js').Activity,
      ProgressOverlay = require('./overlays.js').Progress,
      foundation = require('./foundation.js'),
      util = require('../util.js'),
      row = foundation.row,
      column = foundation.column,
      modal = foundation.modal,
      confirmModal = foundation.confirmModal,
      ActionBar, WorkflowItem;

  ActionBar = React.createClass({
    displayName: "ActionBar",
    getInitialState: function() {
      return {
        actionDropdownVisible: false,
        dropdownWidth: undefined
      };
    },
    toggleActionDropdown: function() {
      this.setState({actionDropdownVisible: !this.state.actionDropdownVisible});
    },
    componentDidUpdate: function() {
      if (this.state.actionDropdownVisible) {
        var domNode = this.getDOMNode();
        var dropdownWidth = this.getDOMNode().getElementsByClassName('action-select')[0]
                            .getBoundingClientRect().width;
        domNode.getElementsByClassName('button-list')[0].style.width = dropdownWidth + "px";
      }
    },
    render: function() {
      return (
        <row>
          <div className="small-6 medium-12 columns">
            {this.props.smallDisplay &&
              <a onClick={this.toggleActionDropdown} className="action-select action-button small dropdown fa fa-list"
                  title="View actions">Actions</a>
            }
            {(!this.props.smallDisplay || this.state.actionDropdownVisible) &&
            <ul className={this.props.smallDisplay ? "button-list": "button-group"}>
              <li>
                <a title="Edit the workflow"
                    href={'/workflow/' + this.props.workflowSlug + '/edit'}
                    className="action-button small">
                    <i className="fa fa-edit"/>{this.props.smallDisplay && " Edit"}
                </a>
              </li>
              <li>
                <a onClick={this.props.removalBlocked ? null : this.props.handleRemove}
                    title="Remove workflow and all associated files"
                    className={"action-button small" + (this.props.removalBlocked ? " disabled" : "")}>
                    <i className="fa fa-trash-o"/>{this.props.smallDisplay && " Remove"}
                </a>
              </li>
              <li>
                <a data-bypass={true}
                    title="Download workflow as a ZIP archive"
                    onClick={this.props.handleDownload}
                    href={'/api/workflow/' + this.props.workflowSlug + '/download'}
                    className="action-button small">
                  <i className="fa fa-download"/>{this.props.smallDisplay && " Download"}
                </a>
              </li>
              {window.config.web.mode !== 'processor' &&
                <li>
                  <a onClick={this.props.handleCapture}
                      title="Capture images"
                      className="action-button small">
                  <i className="fa fa-camera"/>{this.props.smallDisplay && " Capture"}
                </a>
                </li>}
              {window.config.web.standalone_device &&
                <li>
                  <a onClick={this.props.handleTransfer}
                      title="Transfer workflow directory to a removable storage device"
                      className="action-button small">
                    <i className="fa fa-hdd-o"/>{this.props.smallDisplay && " Transfer"}
                  </a>
                </li>}
              {window.config.web.mode === 'scanner' &&
                <li>
                  <a title="Submit for postprocessing"
                      href={'/workflow/' + this.props.workflowSlug + '/submit'}
                      className="action-button small fa">
                    <i className="fa fa-cloud-upload"/>{this.props.smallDisplay && " Submit"}
                  </a>
                </li>}
            </ul>}
          </div>
        </row>
      );
    }
  })

  /**
   * Display a single workflow with thumbnail, metadata and available actions.
   *
   * @property {Workflow} workflow  - Workflow to set configuration for
   */
  WorkflowItem = React.createClass({
    displayName: "WorkflowItem",
    getInitialState: function() {
      return {
        /** Display deletion confirmation modal? */
        deleteModal: false,
        downloadWaiting: false,
        downloadInProgress: false,
        transferWaiting: false,
        transferProgress: 0,
        transferCurrentFile: undefined,
        stepProgress: 0
      };
    },
    /**
     * Remove associated workflow object from the model collection.
     */
    doRemove: function() {
      this.props.workflow.destroy();
    },
    /**
     * Enable deletion confirmation modal
     */
    handleRemove: function() {
      this.setState({
        deleteModal: true
      });
    },
    /**
     * Continue to next step in workflow.
     */
    handleCapture: function() {
      window.router.navigate('/workflow/' + this.props.workflow.get('slug') + '/capture',
                             {trigger: true});
    },
    /**
     * Tries to initiate transfer of associated workflow to an external
     * storage device. Displays an error modal if something goes wrong,
     * otherwise displays a loading overlay as long as the transfer is not
     * completed.
     */
    handleTransfer:  function() {
      this.props.workflow.transfer(function(xhr, status) {
        if (status !== 'success') {
          var data = xhr.responseJSON,
              errorText;
          if (data && data.error) {
            errorText = data.error;
          } else {
            errorText = "Check the server logs for details";
          }
          // Display error modal
          this.setState({
            errorModal: true,
            errorModalHeading: "Transfer failed",
            errorModalText: errorText
          });
        } else {
          // Enable loading overlay
          this.setState({
            transferWaiting: true,
            transferProgress: 0,
            transferCurrentFile: undefined
          });
          // Bind progress events
          window.router.events.on('transfer:progressed', function(data) {
            if (this.isMounted()) {
              this.setState({
                transferProgress: data.progress*100 | 0,
                transferCurrentFile: data.status
              });
            }
          }.bind(this));
          // Register callback for when the transfer is completed
          window.router.events.on('transfer:completed', function() {
            // Disable loading overlay
            this.setState({
              transferWaiting: false
            });
          }.bind(this));
        }
      }.bind(this));
    },
    handleDownload: function() {
      this.setState({
        downloadWaiting: true,
        downloadInProgress: true
      });
      window.router.events.on('download:prepared', function() {
        this.setState({downloadWaiting: false});
      }, this);
      window.router.events.on('download:finished', function() {
        this.setState({downloadInProgress: false});
      }, this);
    },
    render: function() {
      var workflow = this.props.workflow,
          workflowUrl = '/workflow/' + workflow.get('slug'),
          removalBlocked = (this.state.downloadInProgress || this.state.transferWaiting),
          actionBar;

      actionBar = (<ActionBar workflowSlug={workflow.get('slug')}
                              handleRemove={this.handleRemove}
                              handleDownload={this.handleDownload}
                              handleCapture={this.handleCapture}
                              handleTransfer={this.handleTransfer}
                              removalBlocked={removalBlocked}
                              smallDisplay={this.props.smallDisplay}/>);
      return (
        <div>
          <row>
            {/* Display waiting for download overlay? */}
            {this.state.downloadWaiting &&
              <LoadingOverlay message="Preparing download..."/>
            }
            {/* Display deletion confirmation modal? */}
            {this.state.deleteModal &&
              <confirmModal
                onCancel={function(){this.setState({deleteModal: false});}.bind(this)}
                onConfirm={this.doRemove} fixed={true}>
                <h1>Remove?</h1>
                <p>Do you really want to permanently remove this workflow and all
                  of its related files?</p>
              </confirmModal>}
            {/* Display error modal? */}
            {this.state.errorModal &&
              <modal onClose={function(){this.setState({errorModal: false});}.bind(this)}
                    fixed={true}>
                <h1>{this.state.errorModalHeading}</h1>
                <p>{this.state.errorModalText}</p>
              </modal>}
            {/* Display loading overlay */}
            {this.state.transferWaiting &&
              <ProgressOverlay progress={this.state.transferProgress}
                              statusMessage={this.state.transferCurrentFile || "Preparing transfer..."}/>}
            {/* Display preview image (second-to last page) if there are pages
                in the workflow */}
            <column size={[6, 4]}>
            {workflow.get('pages').length > 0 ?
              <a href={workflowUrl}>
                <img width="100%"
                     src={util.getPageUrl(workflow, workflow.get('pages').slice(-2)[0],
                                          'raw', true)} />
              </a>:
              'no pages'
            }
            </column>
            <column size={[6, 8]}>
              <row>
                <column>
                  <h3><a title="View details"
                      href={workflowUrl}>{workflow.get('name')}</a></h3>
                </column>
              </row>
              <row>
                <column>
                  <p>{workflow.has('pages') ? workflow.get('pages').length : 0} pages</p>
                </column>
              </row>
              {_.contains(["process", "output"], workflow.get('status').step) &&
              <row>
                <column>
                  {workflow.get('status').step}:
                  <div className="progress">
                    <span className="meter" style={{width: workflow.get('status').step_progress*100}}></span>
                  </div>
                </column>
              </row>}
              {!this.props.smallDisplay && actionBar}
            </column>
          </row>
          {this.props.smallDisplay && actionBar}
        </div>
      );
    }
  });

  /**
   * Container component that holds all WorkflowItems
   *
   * @property {Backbone.Collection<Workflow>} workflows
   */
  module.exports = React.createClass({
    displayName: "WorkflowList",

    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin],

    /** Activates databinding for `workflows` model collection property. */
    getBackboneModels: function() {
      return [this.props.workflows];
    },
    getInitialState: function() {
      return { mqSmall: util.isSmall() };
    },
    componentWillMount: function() {
      matchMedia(util.mediaQueries.medium).addListener(function(mql){
        this.setState({ mqSmall: !mql.matches});
      }.bind(this));
    },
    render: function() {
      return(
        <main>
          <row>
            <column size='18'>
              <h1>Workflows</h1>
            </column>
          </row>
          <div>
            {this.props.workflows.length > 0 ?
              this.props.workflows.map(function(workflow) {
                return <WorkflowItem key={workflow.id} workflow={workflow}
                                     smallDisplay={this.state.mqSmall}/>;
              }, this):
              <row>
                <column><h2>No workflows yet!</h2>
                <p>
                  Once you have scanned a book, you can see it (and all
                  other books you have scanned so far) and do the following
                  things with it:
                  <ul>
                    <li>Open its detailed view</li>
                    <li>Edit its configuration</li>
                    <li>Delete it</li>
                    <li>Download it</li>
                    <li>Open its capture view</li>
                    <li>Transfer it to a removable storage device</li>
                    <li>Upload it to a remote postprocessing server</li>
                  </ul>
                </p>
                <p>
                  <a className="button" href="/workflow/new">Create a new workflow</a>
                </p></column>
              </row>}
          </div>
        </main>
      );
    }
  });
}());

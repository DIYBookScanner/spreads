/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';
  var React = require('react/addons'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      LoadingOverlay = require('./overlays.js').Activity,
      ProgressOverlay = require('./overlays.js').Progress,
      foundation = require('./foundation.js'),
      row = foundation.row,
      column = foundation.column,
      modal = foundation.modal,
      confirmModal = foundation.confirmModal,
      WorkflowItem;

  /**
   * Display a single workflow with thumbnail, metadata and available actions.
   *
   * @property {Workflow} workflow  - Workflow to set configuration for
   */
  WorkflowItem = React.createClass({
    getInitialState: function() {
      return {
        /** Display deletion confirmation modal? */
        deleteModal: false
      };
    },
    /**
     * Remove associated workflow object from the model collection.
     */
    doRemove: function() {
      this.props.workflow.destroy();
      // Disable deletion confirmation modal
      this.setState({
        deleteModal: false
      });
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
      window.router.navigate('/workflow/' + this.props.workflow.id + '/capture',
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
    render: function() {
      var workflow = this.props.workflow,
          workflowUrl = '#/workflow/' + workflow.get('id');
      return (
        <row>
          {/* Display deletion confirmation modal? */}
          {this.state.deleteModal &&
            <confirmModal
              onCancel={function(){this.setState({deleteModal: false});}.bind(this)}
              onConfirm={this.doRemove}>
              <h1>Remove?</h1>
              <p>Do you really want to permanently remove this workflow and all
                 of its related files?</p>
            </confirmModal>}
          {/* Display error modal? */}
          {this.state.errorModal &&
            <modal onClose={function(){this.setState({errorModal: false});}.bind(this)}>
              <h1>{this.state.errorModalHeading}</h1>
              <p>{this.state.errorModalText}</p>
            </modal>}
          <column size={[6, 3]}>
          {/* Display loading overlay */}
          {this.state.transferWaiting &&
            <ProgressOverlay progress={this.state.transferProgress}
                             statusMessage={this.state.transferCurrentFile || "Preparing transfer..."}/>}
          {/* Display preview image (second-to last page) if there are images
              in the workflow */}
          {workflow.get('images').length > 0 ?
            <a href={workflowUrl}>
              <img width="100%" src={workflow.get('images').slice(-2)[0] + '/thumb'} />
            </a>:
            'no images'
          }
          </column>
          <column size={[6, 9]}>
            <row><h3><a href={workflowUrl}>{workflow.get('name')}</a></h3></row>
            <row>
              <p>{workflow.has('images') ? workflow.get('images').length : 0} pages</p>
            </row>
            <row>
              <ul className="button-group">
                <li><a href={'/#/workflow/' + workflow.id + '/edit'} className="action-button fi-pencil"></a></li>
                <li><a onClick={this.handleRemove} className="action-button fi-trash"></a></li>
                <li><a href={'/workflow/' + workflow.id + '/download'} className="action-button fi-download"></a></li>
                {window.config.web.mode !== 'postprocessor' &&
                  <li><a onClick={this.handleCapture} className="action-button fi-camera"></a></li>}
                {window.config.web.standalone_device &&
                  <li><a onClick={this.handleTransfer} className="action-button fi-usb"></a></li>}
              </ul>
            </row>
          </column>
        </row>
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
      return this.props.workflows;
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
                  return <WorkflowItem key={workflow.id} workflow={workflow} />;
                }):
            <row><column><h2>No workflows yet!</h2></column></row>}
          </div>
        </main>
      );
    }
  });
}());

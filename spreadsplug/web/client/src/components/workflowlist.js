/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';
  var React = require('react/addons'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      LoadingOverlay = require('./loadingoverlay.js'),
      foundation = require('./foundation.js'),
      row = foundation.row,
      column = foundation.column,
      modal = foundation.modal,
      confirmModal = foundation.confirmModal,
      WorkflowItem;

  WorkflowItem = React.createClass({
    getInitialState: function() {
      return {
        deleteModal: false
      };
    },
    doRemove: function() {
      this.props.workflow.destroy({wait: true});
      this.setState({
        deleteModal: false
      });
    },
    handleRemove: function() {
      this.setState({
        deleteModal: true
      });
    },
    handleContinue: function() {
      // TODO: Perform next step, depending on mode we're running in
      window.router.navigate('/workflow/' + this.props.workflow.id + '/capture',
                             {trigger: true});
    },
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
          this.setState({
            errorModal: true,
            errorModalHeading: "Transfer failed",
            errorModalText: errorText
          });
        } else {
          this.setState({
            transferWaiting: true
          });
          this.props.workflow.on('change:step_done', function() {
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
          {this.state.deleteModal &&
            <confirmModal
              onCancel={function(){this.setState({deleteModal: false});}.bind(this)}
              onConfirm={this.doRemove}>
              <h1>Remove?</h1>
              <p>Do you really want to permanently remove this workflow and all
                 of its related files?</p>
            </confirmModal>}
          {this.state.errorModal &&
            <modal onClose={function(){this.setState({errorModal: false});}.bind(this)}>
              <h1>{this.state.errorModalHeading}</h1>
              <p>{this.state.errorModalText}</p>
            </modal>}
          <column size={[6, 3]}>
          {this.state.transferWaiting &&
            <LoadingOverlay message="Please wait for the transfer to finish." />}
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
                <li><a onClick={this.handleRemove} className="action-button fi-trash"></a></li>
                <li><a href={'/workflow/' + workflow.id + '/download'} className="action-button fi-download"></a></li>
                <li><a onClick={this.handleContinue} className="action-button fi-play"></a></li>
                {window.config.web.standalone_device &&
                  <li><a onClick={this.handleTransfer} className="action-button fi-usb"></a></li>}
              </ul>
            </row>
          </column>
        </row>
      );
    }
  });

  module.exports = React.createClass({
    mixins: [ModelMixin],
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

/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';
  var React = require('react/addons'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      foundation = require('./foundation.js'),
      row = foundation.row,
      column = foundation.column,
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
          <column size={[6, 3]}>
          {workflow.get('images').length > 0 ?
            <a href={workflowUrl}>
              <img width="100%" src={workflow.get('images').slice(-1)[0] + '/thumb'} />
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
                <li><a onClick={this.handleRemove} className="button fi-trash"></a></li>
                <li><a href={'/workflow/' + workflow.id + '/download'} className="button fi-download"></a></li>
                <li><a onClick={this.handleContinue} className="button fi-play"></a></li>
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

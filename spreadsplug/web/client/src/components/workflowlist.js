/** @jsx React.DOM */
/* global require, module */
(function() {
  'use strict';
  var React = require('react/addons'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      foundation = require('./foundation.js'),
      row = foundation.row,
      column = foundation.column,
      WorkflowRow;

  WorkflowRow = React.createClass({
    handleRemove: function() {
      // TODO: Ask for verification
      this.props.workflow.destroy({wait: true});
    },
    handleContinue: function() {
      // TODO: Perform next step, depending on mode we're running in
      window.router.navigate('/workflow/' + this.props.workflow.id + '/capture',
                             {trigger: true});
    },
    render: function() {
      var workflow = this.props.workflow;
      return (
        <tr>
          <td><a href={'#/workflow/' + workflow.get('id')}>{workflow.get('name')}</a></td>
          {workflow.has('current_step') ?
            <td>{workflow.get('current_step')}{': '}{workflow.get('finished') ? '' : <em>in progress</em>}</td>:
            <td><em>inactive</em></td>
          }
          <td>
            {workflow.has('images') ? workflow.get('images').length : 0}
          </td>
          <td>
            <a onClick={this.handleRemove} className="fi-trash"></a>
            <a href={'/workflow/' + workflow.id + '/download'} className="fi-download"></a>
            <a onClick={this.handleContinue} className="fi-play"></a>
          </td>
        </tr>
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
          <row>
            <column size={[12, 8, 6]}>
              {this.props.workflows ?
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Images</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {this.props.workflows.map(function(workflow) {
                    return <WorkflowRow key={workflow.id} workflow={workflow} />;
                  })}
                </tbody>
              </table>:
              <h2>No workflows yet!</h2>}
            </column>
          </row>
        </main>
      );
    }
  });
}());

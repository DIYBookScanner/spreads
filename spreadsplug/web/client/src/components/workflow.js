/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';

  var React = require('react/addons'),
      ModelMixin = require('../workflow.js'),
      foundation = require('./foundation.js'),
      row = foundation.row,
      column = foundation.column;

  module.exports = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    render: function() {
      var workflow = this.props.workflow;
      return (
        <main>
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
          <row>
            <column size='12'>
              <h2>Captured images</h2>
              <ul className="small-block-grid-8">
                {workflow.has('images') ?
                  workflow.get('images').map(function(image) {
                    return (
                      <li key={image}><a className="th"><img src={image + '/thumb'} /></a></li>
                    );
                  })
                  :''}
              </ul>
            </column>
          </row>
          <row>
            <column size='12'>
              <h2>Output files</h2>
              <ul>
                {workflow.has('output_files') ?
                  workflow.get('output_files').map(function(outFile) {
                    return (
                      <li key={outFile}><a href={outFile}>{outFile}</a></li>
                    );
                  })
                  :''}
              </ul>
            </column>
          </row>
        </main>
      );
    }
  });
}());

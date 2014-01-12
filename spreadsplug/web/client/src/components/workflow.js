/** @jsx React.DOM */
/* global require */
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
      var workflow = this.props.workflow,
          currentStep;
      /* jshint ignore:start */
      if (!workflow.has('current_step')) {
      } else {
      }
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
                {workflow.has('current_step') ?
                  <li>{workflow.get('current_step')}{': '}
                      {workflow.get('finished') ? '' : <em>in progress</em>}</li>:
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
                  workflow.get('output_files').map(function(out_file) {
                    return (
                      <li key={out_file}><a href={out_file}>{out_file}</a></li>
                    );
                  })
                  :''}
              </ul>
            </column>
          </row>
        </main>
      );
      /* jshint ignore:end */
    }
  });
}());

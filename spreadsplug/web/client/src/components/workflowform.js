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
      _ = require('underscore'),
      merge = require('react/lib/merge'),
      F = require('./foundation.js'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      MetadataEditor = require('./metaeditor.js').MetadataEditor,
      Configuration = require('./config.js').Configuration;

  /**
   * View component for workflow creation
   */
  var WorkflowForm = React.createClass({
    propTypes: {
      workflow: React.PropTypes.object,
      isNew: React.PropTypes.bool,
      globalConfig: React.PropTypes.object
    },

    /** Enables two-way databinding with Backbone model */
    mixins: [ModelMixin],

    /** Activates databinding for `workflow` model property. */
    getBackboneModels: function() {
      return [this.props.workflow];
    },

    getInitialState: function() {
      return {
        /** Errors from validation */
        errors: {},
        /** Whether we are currently submitting */
        submitting: false
      };
    },

    componentDidMount: function() {
      /* Update `errors` if there were validation errors. */
      this.props.workflow.on('validated:invalid', function(workflow, errors) {
        this.setState({errors: errors});
      }, this);
    },

    componentWillUnmount: function() {
      /* Deregister event handlers */
      this.props.workflow.off('all', null, this);
    },

    handleSave: function() {
      this.props.workflow.set('metadata', this.refs.metadata.state.metadata);
      this.props.workflow.set('config', this.refs.config.state.config);
      /* Save workflow and open capture screen when successful */
      this.setState({submitting: true});
      //this.props.workflow.set('metadata', this.refs.metadata.value());
      var rv = this.props.workflow.save({wait: true});
      if (!rv) {
        this.setState({submitting: false});
        return;
      }
      rv.success(function(workflow) {
        var route;
        if (this.props.isNew) {
          route = '/workflow/' + this.props.workflow.get('slug') + '/capture';
        } else {
          route = '/';
        }
        window.router.navigate(route, {trigger: true});
      }.bind(this));
      rv.fail(function(xhr) {
        if (_.isUndefined(xhr.responseJSON)) return;
        this.setState({errors: merge(this.state.errors, xhr.responseJSON.errors)});
      }.bind(this));
      rv.complete(function() {
        if (this.isMounted()) {
          this.setState({submitting: false});
        }
      }.bind(this));
    },

    render: function() {
      return (
        <section>
          <form>
            <F.Row>
              <F.Column>
                <h2>{this.props.isNew ? 'Create workflow' : 'Edit workflow'}</h2>
              </F.Column>
            </F.Row>
            <MetadataEditor ref="metadata" metadata={this.props.workflow.get('metadata')}
                            errors={this.state.errors.metadata}/>
            <Configuration ref="config"
                           config={this.props.workflow.get('config')}
                           errors={this.state.errors || {}}
                           templates={_.omit(window.configTemplates, 'core', 'web')}
                           defaultConfig={this.props.globalConfig}/>
            <F.Row>
              <F.Column>
                <F.Button size='small' disabled={this.state.submitting}
                          onClick={this.handleSave}>
                    <i className="fa fa-check"/> Submit
                </F.Button>
                </F.Column>
            </F.Row>
          </form>
        </section>
      );
    }
  });

  module.exports = WorkflowForm;
}());

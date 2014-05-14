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
      foundation = require('./foundation.js'),
      ModelMixin = require('../../vendor/backbonemixin.js'),
      PluginConfiguration = require('./config.js').PluginConfiguration,
      row = foundation.row,
      column = foundation.column,
      fnButton = foundation.button;

  /**
   * View component for workflow creation
   *
   * @property {Workflow} workflow - Workflow to display
   */
  module.exports = React.createClass({
    displayName: "WorkflowForm",

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
      /* When workflow is saved, add it to the `workflows` collection. */
      // TODO: Check that the workflow is not already in the collection
      //       (happens when editing an existing workflow)
      if (this.props.isNew) {
        this.props.workflow.on('sync', function() {
            this.props.workflow.collection.add(this.props.workflow);
        }, this);
      }
    },
    componentWillUnmount: function() {
      /* Deregister event handlers */
      this.props.workflow.off('all', null, this);
    },
    handleSave: function() {
      /* Save workflow and open capture screen when successful */
      this.setState({submitting: true});
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
        }.bind(this)).error(function(xhr) {
          this.setState({errors: merge(this.state.errors, xhr.responseJSON.errors)});
        }.bind(this))
        .complete(function() {
          if (this.isMounted()) {
            this.setState({submitting: false});
          }
        }.bind(this));
    },
    render: function() {
      return (
        <section>
          <form onSubmit={this.handleSave}>
            <row>
                <column size='12'>
                <h2>{this.props.isNew ?
                        'Create workflow' :
                        'Edit workflow ' + this.props.workflow.get('name')}
                </h2>
                </column>
            </row>
            <row>
                <column size={[12, 9]}>
                <label>Workflow name</label>
                <input type="text" placeholder="Workflow name"
                        valueLink={this.bindTo(this.props.workflow, 'name')}
                />
                {this.state.errors.name && <small className="error">{this.state.errors.name}</small>}
                </column>
            </row>
            <PluginConfiguration workflow={this.props.workflow}
                                 errors={this.state.errors}
                                 templates={window.pluginTemplates}/>
            <row>
                <column size='12'>
                  <button className={"action-button small" + (this.state.submitting ? 'disabled' : '')}>
                    <i className="fi-check"/> Submit
                  </button>
                </column>
            </row>
          </form>
        </section>
      );
    }
  });
}());

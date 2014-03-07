/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      _ = require('underscore'),
      foundation = require('./foundation.js'),
      ModelMixin = require('../../lib/backbonemixin.js'),
      row = foundation.row,
      column = foundation.column,
      PluginOption, PluginWidget, PluginConfiguration;

  // Some helper mixins for underscore that we're going to need
  _.mixin({
    capitalize: function(string) {
        return string.charAt(0).toUpperCase() + string.substring(1).toLowerCase();
      }
  });

  PluginOption = React.createClass({
    render: function() {
      var name = this.props.name,
          option = this.props.option,
          bindFunc = this.props.bindFunc,
          label =  <label htmlFor={name}>{option.docstring || _.capitalize(name)}</label>,
          input;
      if (option.selectable && _.isArray(option.value)) {
        // Dropdown
        input = (
          <select id={name} multiple={!option.selectable} valueLink={bindFunc(name)}>
            {_.map(option.value, function(key) {
              return <option value={key}>{key}</option>;
            })}
          </select>
        );
      } else if (_.isArray(option.value)) {
        input = <em>oops</em>;
      } else if (typeof option.value === "boolean") {
        input = <input id={name} type={"checkbox"} checkedLink={bindFunc(name)} />;
      } else {
        var types = { "number": "number",
                      "string": "text" };

        input = <input id={name} type={types[typeof option.value]} valueLink={bindFunc(name)} />;
      }
      return (
        <row>
          <column size='12'>
            {input.props.type === 'checkbox' ? input : label}
            {input.props.type === 'checkbox' ? label : input}
            {this.props.error ? <small className="error">{this.props.error}</small>: ''}
          </column>
        </row>
      );
    }
  });

  PluginWidget = React.createClass({
    render: function() {
      var template = this.props.template;
      return (
        <row>
          <column size='12'>
            <row>
              <column size='12'>
                <h3>{this.props.plugin}</h3>
              </column>
            </row>
            {_.map(template, function(option, key) {
              var path = 'config.' + this.props.plugin + '.' + key;
              return (<PluginOption name={key} option={option}
                                    bindFunc={this.props.bindFunc}
                                    error={this.props.errors[path]} />);
            }, this)}
          </column>
        </row>
      );
    }
  });

  PluginConfiguration = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return {selectedPlugin: undefined};
    },
    handleSelect: function(event) {
      this.setState({selectedPlugin: event.target.value});
    },
    render: function() {
      var templates = window.pluginTemplates,
          selectedPlugin = this.state.selectedPlugin || _.keys(templates)[0];
      if (_.isEmpty(templates)) {
        return <row />;
      }
      return (
        <row>
          <column size='12'>
            <label>Configure plugin</label>
            <select onChange={this.handleSelect}>
              {_.keys(templates).map(function(plugin) {
                return <option value={plugin}>{_.capitalize(plugin)}</option>;
              })}
            </select>
            {/* NOTE: This is kind of nasty.... We can't use _'s 'partial',
                      since we want to provide the second argument and leave
                      the first one to the caller. */}
            <PluginWidget plugin={selectedPlugin}
                          template={templates[selectedPlugin]}
                          bindFunc={function(key) {
                            return this.bindTo(
                              this.props.workflow,
                              'config.' + selectedPlugin + '.' + key);
                          }.bind(this)}
                          errors={this.props.errors}/>
          </column>
        </row>
      );
    }
  });

  module.exports = React.createClass({
    mixins: [ModelMixin],
    getBackboneModels: function() {
      return [this.props.workflow];
    },
    getInitialState: function() {
      return { errors: {} };
    },
    componentDidMount: function() {
      // Register event handlers
      this.props.workflow.on('validated:invalid', function(workflow, errors) {
        this.setState({errors: errors});
      }, this);
      this.props.workflow.on('sync', function() {
          this.props.workflow.collection.add(this.props.workflow);
      }, this);
    },
    componentWillUnmount: function() {
      // Deregister event handlers
      this.props.workflow.off('validated:invalid');
      this.props.workflow.off('all');
    },
    handleSubmit: function() {
      this.props.workflow.save().success(function(workflow) {
        window.router.navigate('/workflow/' + workflow.id + '/capture',
                               {trigger: true});
      });
      // TODO: Error handling
    },
    render: function() {
      return (
        <section>
          <row>
            <column size='12'>
              <h2>{this.props.workflow.get('id') ?
                    'Edit workflow ' + this.props.workflow.get('name'):
                    'Create workflow'}
              </h2>
            </column>
          </row>
          <row>
            <column size={[12, 9]}>
              <label>Workflow name</label>
              <input type="text" placeholder="Workflow name"
                     valueLink={this.bindTo(this.props.workflow, 'name')}
              />
              {this.state.errors.name ? <small className="error">{this.state.errors.name}</small>: ''}
            </column>
          </row>
          <PluginConfiguration workflow={this.props.workflow}
                               errors={this.state.errors} />
          <row>
            <column size='12'>
              <a onClick={this.handleSubmit} className="button small fi-tick"> Submit</a>
            </column>
          </row>
        </section>
      );
    }
  });
}());

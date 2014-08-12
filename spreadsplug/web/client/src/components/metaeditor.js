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
      merge = require('react/lib/merge'),
      _ = require('underscore'),
      jQuery = require('jquery'),
      F = require('./foundation.js');


  var AutoComplete = React.createClass({
    propTypes: {
      onClick: React.PropTypes.func
    },

    render: function() {
      var data = this.props.data,
          desc = "";
      if (_.has(data, 'creator')) desc += data.creator.join("/") + ": ";
      desc += (data.title || "");
      if (_.has(data, 'date')) desc += " (" + data.date + ")";
      return (
        <li onClick={this.props.onClick}>{desc}</li>
      );
    }
  });


  /**
  * this component is the parent of AutoComplete
  */
  var AutoCompleteBox = React.createClass({
    propTypes: {
      list: React.PropTypes.array,
      onSelect: React.PropTypes.func
    },

    render: function() {
      var enumerated = _.zip(_.range(this.props.list.length), this.props.list);
      var nodes = _.map(enumerated, function(item){
        var key = item[0];
        var data = item[1];
        return <AutoComplete key={key} data={data}
                             onClick={_.partial(this.props.onSelect, data)} />
      }, this);
      return (
        <ul className="autocomplete-suggestions">
          {nodes}
        </ul>
      );
    }
  });


  var AutocompleteField = React.createClass({
    propTypes: {
      key: React.PropTypes.string,
      value: React.PropTypes.string,
      name: React.PropTypes.string,
      error: React.PropTypes.string,
      onChange: React.PropTypes.func,
    },

    getInitialState: function() {
      return {
        completeEnabled: true,
        autocomplete: [],
        lastTerm: '',
        call: { latest: 0,
                term: '' }
      };
    },

    makeCall: _.debounce(function(term, current) {
      var endpoint = "/api/isbn?q=" + encodeURIComponent(term);
      jQuery.ajax({
        url: endpoint,
        success: function(data) {
          /* This ensures that we ignore out of order ajax calls and that the
            last call will win.
            NOTE: an alternative could have been to use jquery's beforeSend
            callback to abort the previous call but that would have required an
            enclosing mutable reference to the previous XHR object. */
          if (current == this.state.call.latest) {
            var newPriority = this.state.call.latest - 1;
            this.setState({
              autocomplete: data.results,
              lastTerm: this.state.call.term,
              call: { latest: newPriority,
                      term: ''}
            });
          }
        }.bind(this),
        error: function() {
          this.setState({completeEnabled: false});
        }.bind(this)
      });
    }, 500),

    //set state if user enters at least 3 chars, also reset state if user clears input box.
    handleKeyUp: function (e) {
      var k = e.target.value;
      if (k.length > 3 && k != this.state.lastTerm) {
        var priority = this.state.call.latest+1;
        this.setState({
          call: { latest: priority,
                  term: k }
        });
      }
      if (k.length == 0) {
        this.setState({
          completeEnabled: true,
          autocomplete: [],
          call: { latest: 0,
                  term: '' }
          });
      }
      return false;
    },

    handleSelect: function(item) {
      this.setState({
        completeEnabled: false,
        autocomplete: [],
        call: { latest: 0,
                term: '' }
      });
      _.each(item, function(value, key) {
        delete item[key];
        item[key.toLowerCase()] = value;
      });
      this.props.onChange(item);
    },

    render: function() {
      // if the incoming state contains a search term with a real priority then
      // make the async ajax/json calls
      if (this.state.call.latest > 0 && this.state.call.term != '' && this.state.completeEnabled) {
        this.makeCall(this.state.call.term, this.state.call.latest);
      }
      return (
        <div>
          <F.Row>
            <F.Column size={2}>
              <label htmlFor={this.props.key + "-input"} className="right inline">
                {this.props.name}
              </label>
            </F.Column>
            <F.Column size={10}>
              <input type="text" placeholder="Enter a search-term to get a list of suggestions"
                     value={this.props.value} ref="input"
                     id={this.props.key + "-input"}
                     onChange={function(e){
                       this.props.onChange({'title': e.target.value});
                     }.bind(this)}
                     onKeyUp={this.handleKeyUp}/>
              {this.props.error &&
                <small className="error">{this.props.error}</small>
              }
            </F.Column>
          </F.Row>
          <F.Row>
            <F.Column size={10} offset={2}>
              <AutoCompleteBox list={this.state.autocomplete} onSelect={this.handleSelect} />
            </F.Column>
          </F.Row>
        </div>
      );
    }
  });


  var Field = React.createClass({
    propTypes: {
      key: React.PropTypes.string,
      value: React.PropTypes.string,
      error: React.PropTypes.string,
      onChange: React.PropTypes.func
    },

    render: function() {
      return (
        <F.Row>
          <F.Column size={2}>
            <label htmlFor={this.props.key + "-input"} className="right inline">
              {this.props.name}
            </label>
          </F.Column>
          <F.Column size={10}>
            <input type="text" ref="input" value={this.props.value}
                   id={this.props.key + "-input"}
                   onChange={function(e){this.props.onChange(e.target.value)}.bind(this)}/>
            {this.props.error &&
              <small className="error">{this.props.error}</small>
            }
          </F.Column>
        </F.Row>
      );
    }
  });


  var FieldSet = React.createClass({
    propTypes: {
      name: React.PropTypes.string,
      values: React.PropTypes.array,
      errors: React.PropTypes.array,
      onChange: React.PropTypes.func
    },

    onModified: function(idx, value) {
      var values = _.clone(this.props.values);
      values[idx] = value;
      this.props.onChange(values);
    },

    onRemoved: function(idx) {
      var values = _.clone(this.props.values);
      values.splice(idx, 1);
      this.props.onChange(values);
    },

    onAdded: function() {
      var values = _.clone(this.props.values);
      if (_.isEmpty(values)) values.push("");
      values.push("");
      this.props.onChange(values);
    },

    render: function() {
      var values = this.props.values,
          enumeratedValues,
          canBeRemoved = !(_.isEmpty(values) || (values.length == 1 && _.isEmpty(values[0])));
      if (_.isEmpty(values)) values = [""];
      enumeratedValues = _.zip(_.range(values.length), values);
      return (
        <F.Row className="metadata-fieldset">
          <F.Column size={2}><label>{this.props.name}</label></F.Column>
          <F.Column size={10}>
          {_.map(enumeratedValues, function(value) {
            return (
            <F.Row key={value[0]} collapse={true}>
              <F.Column size={10}>
                <input ref={'field-' + value[0]} type="text" value={value[1]}
                      onChange={function(e) {
                                  this.onModified(value[0], e.target.value)
                                }.bind(this)} />
                {!_.isUndefined(this.props.errors[value[0]]) &&
                  <small className="error">{this.props.errors[value[0]]}</small>
                }
              </F.Column>
              {canBeRemoved &&
                <F.Column size={1}>
                  <span className="postfix" onClick={_.partial(this.onRemoved, value[0])}>
                    <i className="fa fa-times" />
                  </span>
                </F.Column>}
              <F.Column size={canBeRemoved ? 1 : 2}>
                {value[0] === values.length-1 &&
                 <span className="postfix" onClick={this.onAdded}>
                   <i className="fa fa-plus" />
                 </span>}
              </F.Column>
            </F.Row>);
          }, this)}
          </F.Column>
        </F.Row>);
    }
  });


  var MetadataEditor = React.createClass({
    propTypes: {
      metadata: React.PropTypes.object,
      errors: React.PropTypes.object
    },

    updateMetadata: function(newData) {
      if (_.isUndefined(this.state.metadata.title) && _.has(newData, 'identifier')) {
        var isbnNo = _.find(newData.identifier, function(val) {
          return val.slice(0,5) === "ISBN:";
        });
        if (!_.isUndefined(isbnNo)) {
          this.updateFromISBN(isbnNo, newData.identifier.indexOf(isbnNo));
        } else if (!_.isUndefined(this.state.errors.identifier)) {
          var errors = _.clone(this.state.errors);
          errors.identifier = [];
          this.setState({errors: errors});
        }
      }
      this.setState({
        metadata: merge(this.state.metadata, newData)
      });
    },

    updateFromISBN: function(isbnNo, inputIdx) {
      jQuery.ajax({
        url: "/api/isbn/" + isbnNo,
        dataType: 'json',
        timeout: 3000,
        success: function(data) {
          var errors = _.clone(this.state.errors),
              idErrors = errors.identifier || [];
          delete idErrors[inputIdx];
          this.setState({errors: errors});
          this.updateMetadata(data);
        }.bind(this),
        error: function(xhr) {
          if (xhr.status != 400) return;
          var errors = _.clone(this.state.errors),
              idErrors = errors.identifier || [];
          idErrors[inputIdx] = xhr.responseJSON.errors.isbn;
          errors.identifier = idErrors;
          this.setState({errors: errors});
        }.bind(this)
      });
    },

    getInitialState: function() {
      return {
        // NOTE: This is only for initialization purposes
        metadata: this.props.metadata || {},
        errors: this.props.errors || {}
      }
    },

    render: function() {
      var errors = merge(this.state.errors, this.props.errors || {});
      return (
        <F.Row>
          <F.Column size={[12, 10, 8]}>
            <fieldset className="metadata">
              <legend>Metadata</legend>
              {_.map(window.metadataSchema, function(field) {
                if (field.key === 'title') {
                  return <AutocompleteField name={field.description} key={field.key}
                                            value={this.state.metadata[field.key]}
                                            error={errors.title}
                                            onChange={this.updateMetadata} />;
                } else if (field.multivalued) {
                  return <FieldSet name={field.description} key={field.key}
                                   values={this.state.metadata[field.key] || []}
                                   errors={errors[field.key] || []}
                                   onChange={function(values) {
                                     var update = {};
                                     update[field.key] = values
                                     this.updateMetadata(update);
                                   }.bind(this)} />;
                } else {
                  return <Field name={field.description} key={field.key}
                                value={this.state.metadata[field.key]}
                                errors={errors[field.key]}
                                onChange={function(value) {
                                  var update = {};
                                  update[field.key] = value;
                                  this.updateMetadata(update);
                                }.bind(this)} />;
                }
              }, this)}
            </fieldset>
          </F.Column>
        </F.Row>
      );
    }
  });

  module.exports = {
    MetadataEditor: MetadataEditor
  };
}());

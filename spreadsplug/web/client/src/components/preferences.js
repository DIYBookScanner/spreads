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
      Overlay = require('./overlays.js').Overlay,
      LayeredComponentMixin = require('./overlays.js').LayeredComponentMixin,
      Configuration = require('./config.js').Configuration;

  var Preferences = React.createClass({
    mixins: [LayeredComponentMixin],

    propTypes: {
      globalConfig: React.PropTypes.object.isRequired,
      onSave: React.PropTypes.func.isRequired,
      errors: React.PropTypes.object
    },

    getDefaultProps: function() {
      return {
        errors: {
          preferences: {},
          displayRestartConfirmation: false
        }
      };
    },

    getInitialState: function() {
      return {
        config: this.props.globalConfig,
      }
    },

    doSave: function(force) {
      var restartRequired = _.any(['core', 'web'], function(section) {
        return !_.isEqual(this.props.globalConfig[section],
                          this.refs.config.state.config[section]);
      }, this);
      if (restartRequired && !force) {
        this.setState({displayRestartConfirmation: true})
      } else {
        this.props.onSave(this.refs.config.state.config);
      }
    },

    handleSave: function() {
      this.doSave();
    },

    render: function() {
      return (
        <section>
          <form>
            <F.Row><F.Column><h2>Preferences</h2></F.Column></F.Row>
                <Configuration ref="config" config={this.props.globalConfig}
                               errors={this.props.errors} enableCore={true}
                               templates={window.configTemplates} />
            <F.Row>
              <F.Column>
                <F.Button size='small' onClick={this.handleSave}>
                  <i className="fa fa-check"> Save</i>
                </F.Button>
              </F.Column>
            </F.Row>
          </form>
        </section>
      );
    },

    renderLayer: function() {
      if (!this.state.displayRestartConfirmation) return null;
      var closeModal = _.partial(this.setState.bind(this),
                                 {displayRestartConfirmation: false},
                                 null);
      return (
        <Overlay>
          <F.Modal onClose={closeModal}>
            <F.Row>
              <F.Column><h1>Restart required</h1></F.Column>
            </F.Row>
            <F.Row>
              <F.Column><p>
                You seem to have made changes to either the <strong>core</strong>
                or <strong>web</strong> settings. This makes it neccessary to restart
                the application. Please make sure that nobody else is using the scanner at
                the moment.</p>
              <p>It is also strongly advised to <strong>refresh the page</strong> if you
                 have made any changes to the <strong>web</strong> configuration.
              </p></F.Column>
            </F.Row>
            <F.Row>
              <F.Column size={6}>
                <F.Button onClick={function(){ this.doSave(true); closeModal(); }.bind(this)}
                          size="small">OK</F.Button>
              </F.Column>
              <F.Column size={6}>
                <F.Button onClick={closeModal} size="small">Cancel</F.Button>
              </F.Column>
            </F.Row>
          </F.Modal>
        </Overlay>
      );
    }

  });

  module.exports = Preferences;
}());

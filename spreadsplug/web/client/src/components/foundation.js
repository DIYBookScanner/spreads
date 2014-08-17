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
      classSet = React.addons.classSet,
      _ = require('underscore');

  /**
   * Row component.
   */
  var Row =  React.createClass({
    propTypes: {
      /** Useful for pre/postfix labels in forms */
      collapse: React.PropTypes.bool,
      /** Additional CSS classes */
      className: React.PropTypes.string,
      /** Child component(s) */
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ]),
    },

    getDefaultProps: function() {
      return {
        collapse: false,
        className: ""
      }
    },

    render: function() {
      var classes = [
        this.props.className,
        classSet({
          'row': true,
          'collapse': this.props.collapse
        })
      ].join(" ");
      return (<div className={classes}>{this.props.children}</div>);
    }
  });


  /**
   * Column component
   */
  var Column = React.createClass({
    propTypes: {
      size: React.PropTypes.oneOfType([
        React.PropTypes.number,
        React.PropTypes.arrayOf(React.PropTypes.number)
      ]),
      offset: React.PropTypes.oneOfType([
        React.PropTypes.number,
        React.PropTypes.arrayOf(React.PropTypes.number)
      ]),
      className: React.PropTypes.string,
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ]),
    },

    getDefaultProps: function() {
      return {
        size: 12,
        offset: 0
      };
    },

    render: function() {
      var classes = {
        columns: true
      };
      if (_.isNumber(this.props.size)) {
        classes['small-' + this.props.size] = true;
      } else {
        _.each(_.zip(this.props.size, ['small', 'medium', 'large']), function(size) {
          if (size[0]) classes[size[1] + '-' + size[0]] = true;
        });
      }
      if (_.isNumber(this.props.offset) && this.props.offset > 0) {
        classes['small-offset-' + this.props.offset] = true;
      } else {
        _.each(_.zip(this.props.offset, ['small', 'medium', 'large']), function(offset) {
          if (offset[0]) classes[offset[1] + '-offset-' + offset[0]] = true;
        });
      }
      var className = [React.addons.classSet(classes), this.props.className].join(" ");
      return (<div className={className}>
                {this.props.children}
              </div>);
    }
  });

  /**
   * Button component.
   */
  var Button = React.createClass({
    propTypes: {
      size: React.PropTypes.oneOf(['tiny', 'small', 'medium', 'large']),
      secondary: React.PropTypes.bool,
      expand: React.PropTypes.bool,
      disabled: React.PropTypes.bool,
      onClick: React.PropTypes.func,
      className: React.PropTypes.string,
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ]),
    },

    getDefaultProps: function() {
      return {
        size: 'medium',
        secondary: false,
        expand: false,
        disabled: false
      };
    },

    render: function() {
      var classes = {
        'action-button': true,  // TODO: Remove
        'secondary': this.props.secondary,
        'expand': this.props.expand,
        'disabled': this.props.disabled
      };
      var className = [classSet(classes), this.props.className].join(" ");
      classes += " " + this.props.size;
      return (<a onClick={this.props.onClick} className={className}>
                {this.props.children}
              </a>);
    }
  });


  /**
   * Display a Foundation "alert" box.
   */
  var Alert = React.createClass({
    propTypes: {
      severity: React.PropTypes.oneOf([
        'standard', 'success', 'warning', 'info', 'alert', 'secondary'
      ]),
      onClick: React.PropTypes.func,
      onClose: React.PropTypes.func,
      className: React.PropTypes.string,
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ])
    },

    getDefaultProps: function() {
      return {
        level: 'standard'
      }
    },

    render: function() {
      var classes = {'alert-box': true};
      classes[this.props.severity] = true;
      var className = [classSet(classes), this.props.className].join(" ");
      return (<div className={className} onClick={this.props.onClick}>
                {this.props.children}
                <a className="close" onClick={this.props.onClose}>&times;</a>
              </div>);
    }
  });


  var PageButton = React.createClass({
    propTypes: {
      current: React.PropTypes.bool,
      num: React.PropTypes.number,
      onClick: React.PropTypes.func
    },

    render: function() {
      return (
        <li className={this.props.current ? "current": ""}>
          <a onClick={this.props.onClick}>
            {this.props.num}
          </a>
        </li>
      );
    }
  });


  /**
   * Pagination component.
   */
  var Pagination = React.createClass({
    propTypes: {
      centered: React.PropTypes.bool,
      pageCount: React.PropTypes.number.isRequired,
      onBrowse: React.PropTypes.func.isRequired
    },

    getDefaultProps: function() {
      return { centered: false };
    },

    /**
     * Switch to previous page
     */
    handleBack: function() {
      if (this.state.currentPage !== 1) {
        this.handleToPage(this.state.currentPage-1);
      }
    },

    /**
     * Switch to next page
     */
    handleForward: function() {
      if (this.state.currentPage !== this.props.pageCount) {
        this.handleToPage(this.state.currentPage+1);
      }
    },

    /**
     * Change to given page
     *
     * @param {number} idx - Page number to switch to
     */
    handleToPage: function(idx) {
      this.setState({
        currentPage: idx
      });
      this.props.onBrowse(idx);
    },

    getInitialState: function() {
      return {
        currentPage: 1
      };
    },

    render: function() {
      var lastPage = this.props.pageCount,
          currentPage = this.state.currentPage;

      var uncenteredPagination = (
        <ul className="pagination">
          <li className={"arrow" + (currentPage === 1 ? " unavailable" : '')}>
            <a onClick={this.handleBack}>&laquo;</a>
          </li>
          <PageButton current={currentPage === 1} num={1} onClick={_.partial(this.handleToPage, 1)} />
          {(currentPage > 2) && <li className="unavailable"><a>&hellip;</a></li>}
          {lastPage > 2 &&
            _.range(currentPage-1, currentPage+2).map(function(idx) {
              if (idx <= 1 || idx >= lastPage) return;
              return (
                <PageButton key={"page-"+idx} current={currentPage === idx}
                  num={idx} onClick={_.partial(this.handleToPage, idx)} />
              );
            }.bind(this))}
          {(currentPage < lastPage-1) && <li className="unavailable"><a>&hellip;</a></li>}
          <PageButton current={currentPage === lastPage} num={lastPage}
                      onClick={_.partial(this.handleToPage, lastPage)} />
          <li className={"arrow" + (currentPage === lastPage ? " unavailable" : '')}>
            <a onClick={this.handleForward}>&raquo;</a>
          </li>
        </ul>
      );
      if (this.props.centered) {
        return (
          <div className="pagination-centered">
            {uncenteredPagination}
          </div>
        );
      } else {
        return uncenteredPagination;
      }
    }
  });


  /**
   * Modal overlay with close button
   */
  var Modal = React.createClass({
    propTypes: {
      fixed: React.PropTypes.bool,
      small: React.PropTypes.bool,
      onClose: React.PropTypes.func,
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ]),
    },

    getDefaultProps: function() {
      return {
        small: true,
        fixed: true
      };
    },

    render: function() {
      var classes = classSet({
        'reveal-modal': true,
        'open': true,
        'fixed': this.props.fixed,
        'small': this.props.small
      });
      return (
        <div className={classes}
              style={{visibility: 'visible', display: 'block'}}>
          {this.props.children}
          <a className="close-reveal-modal" onClick={this.props.onClose}>&#215;</a>
        </div>
      );
    }
  });


  /**
   * Modal overlay with 'OK' and 'Cancel' buttons.
   */
  var ConfirmModal = React.createClass({
    propTypes: {
      fixed: React.PropTypes.bool,
      onCancel: React.PropTypes.func,
      onConfirm: React.PropTypes.func,
      children: React.PropTypes.oneOfType([
        React.PropTypes.renderable,
        React.PropTypes.arrayOf(React.PropTypes.renderable)
      ])
    },

    getDefaultProps: function() {
      return { fixed: true };
    },

    render: function() {
      return (
        <Modal onClose={this.props.onCancel} fixed={this.props.fixed}>
          {this.props.children}
          <Row>
            <Column size={6}>
              <Button onClick={this.props.onConfirm} size="small">OK</Button>
            </Column>
            <Column size={6}>
              <Button onClick={this.props.onCancel} size="small">Cancel</Button>
            </Column>
          </Row>
        </Modal>
      );
    }
  });

  var Label = React.createClass({
    propTypes: {
      round: React.PropTypes.bool,
      severity: React.PropTypes.oneOf([
        'standard', 'success', 'warning', 'alert', 'secondary'
      ]),
    },

    render: function() {
      var classes = {
        'label': true,
        'round': this.props.round,
      };
      if (this.props.severity !== 'standard') classes[this.props.severity] = true;
      return (
        <span className={classSet(classes)}>{this.props.children}</span>
      );
    }
  });

  module.exports = {
    Row: Row,
    Column: Column,
    Button: Button,
    Alert: Alert,
    Pagination: Pagination,
    Modal: Modal,
    ConfirmModal: ConfirmModal,
    Label: Label
  };
}());

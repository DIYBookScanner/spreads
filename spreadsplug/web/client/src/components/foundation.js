/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      classSet = React.addons.classSet,
      _ = require('underscore'),
      row, column, fnButton, fnAlert, pagination, modal, confirmModal;

  /**
   * Row component.
   *
   * @property {string} className - Additionall CSS classes for the component
   * @property {React.Component[]} children - Child components
   */
  row =  React.createClass({
    render: function() {
      return this.transferPropsTo(<div className="row">{this.props.children}</div>);
    }
  });

  /**
   * Column component
   *
   * @property {string|string[]} [size='12'] - Size of the column.
   *    If specified as a string, the size will be valid for
   *    all sizes. If specified as an array, the values will be for
   *    [small, medium, [large]] sizes, depending on their position.
   * @property {string} [offset='0'] - Horizontal offset of the column.
   * @property {React.Component[]} children - Child components
   */
  column = React.createClass({
    render: function() {
      var classes = this.props.className || '';
      if (typeof this.props.size === 'object') {
        var sizes = this.props.size;
        classes += " small-" + sizes[0] +
                  " medium-" + sizes[1] +
                  " large-" + (sizes[2] || sizes[1])+
                  " columns";
      } else {
        classes += " small-" + (this.props.size || 12) + " columns";
      }
      if (this.props.offset) {
        classes += " small-offset-" + this.props.offset;
      }
      return (<div className={classes}>{this.props.children}</div>);
    }
  });

  /**
   * Button component.
   *
   * @property {function} callback - Callback for button click
   * @property {string} [size] - Button size
   * @property {boolean} [secondary] - Button is secondary
   * @property {boolean} [expand] - Expand button size
   * @property {boolean} [disabled] - Disable the button
   * @property {React.Component[]} children - Child components
   */
  fnButton = React.createClass({
    render: function() {
      var classes = classSet({
        'action-button': true,
        'secondary': this.props.secondary,
        'expand': this.props.expand,
        'disabled': this.props.disabled
      });
      classes += " " + this.props.size;
      return (<a onClick={this.props.callback} className={classes}>
                {this.props.children}
              </a>);
    }
  });

  /**
   * Display a Foundation "alert" box.
   *
   * @property {function} closeCallback - Callback function when alert is closed
   * @property {string} [level] - Severity level of alert (debug/info/warning/error)
   * @property {string} message - Message in alert box
   * @property {React.Component[]} children - Child components
   */
  fnAlert = React.createClass({
    handleClose: function() {
      this.props.closeCallback();
    },
    render: function() {
      var classes = ['alert-box'];
      if (_.contains(['WARNING', 'ERROR'], this.props.level)) {
        classes.push('warning');
      }
      return (<div data-alert
                    className={"alert-box " + classes.join(' ')} >
                {this.props.message}
                {this.props.children}
                <a onClick={this.handleClose} className="close">&times;</a>
              </div>
              );
    }
  });

  /**
   * Pagination component.
   *
   * @property {function} onBrowse - Callback for page changes
   * @property {number} pageCount - Total number of pages
   * @property {boolean} [centered=false] - Center the pagination
   */
  pagination = React.createClass({
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
      this.props.onBrowse(idx);
      this.setState({
        currentPage: idx
      });
    },
    getInitialState: function() {
      return {
        currentPage: 1
      };
    },
    render: function() {
      var pageButton = React.createClass({
        render: function() {
          return (
            <li className={this.props.current ? "current": ""}>
              <a onClick={function() {this.props.onClick(this.props.num);}.bind(this)}>
                {this.props.num}
              </a>
            </li>
          );
        }
      }).bind(this);
      var lastPage = this.props.pageCount,
          currentPage = this.state.currentPage,
          uncenteredPagination;

      uncenteredPagination = (
        <ul className="pagination">
          <li className={"arrow" + (currentPage === 1 ? " unavailable" : '')}>
            <a onClick={this.handleBack}>&laquo;</a>
          </li>
          <pageButton current={currentPage === 1} num={1} onClick={this.handleToPage} />
          {(currentPage > 2) && <li className="unavailable"><a>&hellip;</a></li>}
          {lastPage > 2 &&
            _.range(currentPage-1, currentPage+2).map(function(idx) {
              if (idx <= 1 || idx >= lastPage) return;
              return <pageButton key={"page-"+idx} current={currentPage === idx} num={idx} onClick={this.handleToPage} />;
            }.bind(this))}
          {(currentPage < lastPage-1) && <li className="unavailable"><a>&hellip;</a></li>}
          <pageButton current={currentPage === lastPage} num={lastPage} onClick={this.handleToPage} />
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
   *
   * @property {function} onClose - Callback function when close button is pressed
   * @property {React.Component[]} children - Child components
   */
  modal = React.createClass({
    render: function() {
      return (
        <div className="reveal-modal open"
              style={{visibility: 'visible', display: 'block'}}>
          {this.props.children}
          <a className="close-reveal-modal" onClick={this.props.onClose}>&#215;</a>
        </div>
      );
    }
  });

  /**
   * Modal overlay with 'OK' and 'Cancel' buttons.
   *
   * @property {function} onConfirm - Callback function when confirm button is pressed
   * @property {function} onCancel - Callback when cancel or close button is pressed
   * @property {React.Component[]} children - Child components
   */
  confirmModal = React.createClass({
    render: function() {
      return (
        <modal onClose={this.props.onCancel}>
          {this.props.children}
          <row>
            <column size="6">
              <fnButton callback={this.props.onConfirm} size="small">OK</fnButton>
            </column>
            <column size="6">
              <fnButton callback={this.props.onCancel} size="small">Cancel</fnButton>
            </column>
          </row>
        </modal>
      );
    }
  });

  module.exports = {
    row: row,
    column: column,
    button: fnButton,
    alert: fnAlert,
    pagination: pagination,
    modal: modal,
    confirmModal: confirmModal
  };
}());

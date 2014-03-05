/** @jsx React.DOM */
/* global module, require */
(function() {
  'use strict';
  var React = require('react/addons'),
      _ = require('underscore');

  module.exports = {
    row: React.createClass({
      render: function() {
        var classes = [];
        if (this.props.className) classes.push(this.props.className);
        classes.push('row');
        return (<div className={classes.join(" ")}>{this.props.children}</div>);
      }
    }),
    column: React.createClass({
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
        return (<div className={classes}>{this.props.children}</div>);
      }
    }),
    button: React.createClass({
      render: function() {
        return (<a onClick={this.props.callback}
                   className={(this.props.size || '') +
                              " button" +
                              (this.props.secondary ? " secondary" : '') +
                              (this.props.expand ? " expand" : '')}>
                  {this.props.children}
                </a>
               );
      }
    }),
    alert: React.createClass({
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
                  <a onClick={this.handleClose} className="close">&times;</a>
                </div>
               );
      }
    }),
    pagination: React.createClass({
      handleBack: function() {
        this.handleToPage(this.state.currentPage-1);
      },
      handleForward: function() {
        this.handleToPage(this.state.currentPage+1);
      },
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
        /* TODO: Should be like this:
         * <left> [1] ... [cur-1] [[cur]] [cur+1] ... [n] <right>
         * <left> [1] [[2]] [3] ... [n] <right>
         * <left> [1] ... [n-2] [[n-1]] [n] <right>
         * <left> [[1]] [2] [3] ... [n] <right>
         * <left> [1] ... [n-2] [n-1] [[n]] <right>
         */
        var pageButton = React.createClass({
          render: function() {
            return (
              <li className={this.props.current ? "current": ""}>
                <a onClick={function() {this.props.onClick(this.props.num)}.bind(this)}>
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
            <li className={"arrow" + (currentPage == 1 ? " unavailable" : '')}>
              <a onClick={this.handleBack}>&laquo;</a>
            </li>
            <pageButton current={currentPage == 1} num={1} onClick={this.handleToPage} />
            {(currentPage > 3) ? <li className="unavailable"><a>&hellip;</a></li>:''}
            {lastPage > 2 ? _.range(currentPage-2, currentPage+3).map(function(idx) {
              if (idx <= 1 || idx >= lastPage) return;
              return <pageButton current={currentPage == idx} num={idx} onClick={this.handleToPage} />;
            }.bind(this)):''}
            {(currentPage < lastPage-2) ? <li className="unavailable"><a>&hellip;</a></li>:''}
            <pageButton current={currentPage == lastPage} num={lastPage} onClick={this.handleToPage} />
            <li className={"arrow" + (currentPage == lastPage ? " unavailable" : '')}>
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
    })
  }
}());

/* global module, require */
(function() {
  'use strict';

  var Backbone = require('backbone'),
      Message;

  Message = Backbone.Model.extend({});

  module.exports = Backbone.Collection.extend({
    model: Message,
  });
}());

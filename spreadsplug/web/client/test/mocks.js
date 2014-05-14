var sinon = require("sinon"),
    Backbone = require("backbone"),
    _ = require("underscore"),
    MockRouter,
    Configuration;

MockRouter = function() {}
_.extend(MockRouter.prototype, Backbone.Events, {
  events: _.clone(Backbone.Events)
});

Configuration = {
  web: {
    standalone_device: true
  }
}

module.exports = {
  Configuration: Configuration,
  MockRouter: MockRouter
}

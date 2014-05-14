var sinon = require("imports?define=>false!sinon"),
    Backbone = require("backbone"),
    _ = require("underscore");

window.config = { web: { standalone_device: true }}
window.router = { events: _.clone(Backbone.Events)};

module.exports = {
  config: window.config,
  router: window.router
}

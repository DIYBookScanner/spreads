describe("Router", function() {
  var Router, Workflows, React;
  beforeEach(function() {
    jest.dontMock('../router.js');
    jest.dontMock('jquery');
    var Backbone = require('backbone'),
        React = require('react/addons'),
        jQuery = require('jquery');
    jQuery.ajax = jest.genMockFn();
    React.renderComponent = jest.genMockFn();
    Backbone.$ = jQuery;
    Backbone.history.start({pushState: true, root: '/'});
    Workflows = require('../workflow.js');
    Router = require('../router.js');
  });

  it("Initializes Workflow model collection", function() {
    var router = new Router();
    expect(Workflows.mock.instances.length).toBe(1);
    expect(Workflows.mock.instances[0].connectEvents.mock.calls.length).toBe(1);
    expect(Workflows.mock.instances[0].fetch.mock.calls.length).toBe(1);
  });

  it("Renders SpreadsApp component on routes", function() {
    var router = new Router(),
        SpreadsApp = require('../components/spreadsapp.js');
    router.navigate('workflow/test', {trigger: true});
    expect(SpreadsApp.mock.calls.length).toBe(1);
    expect(SpreadsApp.mock.calls[0][0].view).toBe('view');
    expect(SpreadsApp.mock.calls[0][0].workflowSlug).toBe('test');
    expect(SpreadsApp.mock.calls[0][0].workflows).toBe(Workflows.mock.instances[0]);
  });
});

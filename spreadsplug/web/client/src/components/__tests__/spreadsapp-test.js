describe('SpreadsApp', function() {
  var app, workflows, msgCount, TestUtils;

  function triggerLogRecord(level) {
    var record = {
      level: level,
      message: "An " + level,
      time: Date.now() + msgCount
    };
    msgCount++;
    window.router.events.trigger("logrecord", record);
    return record;
  }

  beforeEach(function() {
    jest.dontMock('../spreadsapp.js');
    var SpreadsApp = require('../spreadsapp.js'),
        Events = require('backbone').Events,
        _ = require('underscore');
    TestUtils = require('react/addons').addons.TestUtils;
    msgCount = 0;
    window.router = _.clone(Events);
    window.router.events = _.clone(Events);
    workflows = {
      where: jest.genMockFn(),
      model: jest.genMockFn(),
      add: jest.genMockFn()
    };
    app = TestUtils.renderIntoDocument(SpreadsApp({ view: "root", workflows: workflows }));
  });

  it('updates document title', function() {
    expect(document.title).toBe('spreads: workflow list');
  });

  it('passes correct props to the navigation bar', function() {
    var NavigationBar = require('../navbar.js');
    triggerLogRecord("ERROR");
    triggerLogRecord("ERROR");
    expect(NavigationBar).toBeCalled();
    expect(NavigationBar.mock.calls.slice(-1)[0][0].numUnreadErrors).toEqual(2);
    expect(NavigationBar.mock.calls.slice(-1)[0][0].title).toEqual(document.title);
  });

  it('renders correct screen for route.', function() {
    var WorkflowList = require('../workflowlist.js');
    expect(WorkflowList).toBeCalled();
  });

  it('creates a new Workflow object before rendering with the WorkflowForm component', function() {
    app.props.view = "create";
    app.forceUpdate();
    expect(workflows.model).toBeCalled();
    expect(workflows.add).toBeCalled();
  });

  xdescribe('MessageArea', function() {
    var fnAlert;

    beforeEach(function() {
      fnAlert = require('../foundation.js').alert;
    });

    it('displays messages when events are triggered.', function(){
      triggerLogRecord("WARNING");
      triggerLogRecord("ERROR");
      triggerLogRecord("INFO");

      var alerts = TestUtils.scryRenderedComponentsWithType(app, fnAlert);
      expect(alerts.length).toBe(2);
    });

    it('only displays the three most recent messages', function() {
      var msg1, msg2, msg3;
      triggerLogRecord("WARNING");
      msg1 = triggerLogRecord("ERROR");
      msg2 = triggerLogRecord("WARNING");
      msg3 = triggerLogRecord("ERROR");

      var alerts = TestUtils.scryRenderedComponentsWithType(app, fnAlert);
      expect(alerts.length).toBe(3);
      expect(alerts[0].props.key).toEqual(msg1.time);
      expect(alerts[2].props.key).toEqual(msg3.time);
      expect(app.state.numUnreadErrors).toBe(4);
    });

    it('removes messages upon clicking them', function() {
      triggerLogRecord("ERROR");
      triggerLogRecord("ERROR");
      var alerts = TestUtils.scryRenderedComponentsWithType(app, fnAlert);
      expect(alerts.length).toBe(2);
      TestUtils.Simulate.click(alerts[0].getDOMNode());
      alerts = TestUtils.scryRenderedComponentsWithType(app, fnAlert);
      expect(alerts.length).toBe(1);
    });

    it('is reset when user navigates to log view.', function() {
      triggerLogRecord("ERROR");
      triggerLogRecord("ERROR");
      window.router.trigger('route:displayLog');
      var alerts = TestUtils.scryRenderedComponentsWithType(app, fnAlert);
      expect(alerts.length).toBe(0);
    });
  });
});

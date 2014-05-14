var React = require('react/addons'),
    TestUtils = React.addons.TestUtils,
    SpreadsApp = require('../../../src/components/spreadsapp.js'),
    fnAlert = require('../../../src/components/foundation.js').alert,
    NavigationBar = require('../../../src/components/navbar.js'),
    WorkflowList = require('../../../src/components/workflowlist.js'),
    WorkflowForm = require('../../../src/components/workflowform.js'),
    Workflows = require('../../../src/workflow.js');

describe('SpreadsApp', function() {
  var app, workflows, msgCount = 0;

  function triggerLogRecord(level) {
    var record = {
      level: level,
      message: "An " + level,
      time: Date.now() + msgCount
    };
    msgCount++;
    window.WebSocket().triggerEvent('logrecord', record);
    return record;
  }

  beforeEach(function() {
    msgCount = 0;
    workflows = new Workflows();
    workflows.connectEvents(window.router.events);
    app = TestUtils.renderIntoDocument(SpreadsApp({ view: "root", workflows: workflows }));
  });

  afterEach(function() {
    if (app.isMounted()) {
      React.unmountComponentAtNode(app.getDOMNode().parentNode);
    }
    window.router.events.off(null, null, workflows);
  });

  it('updates document title', function() {
    expect(document.title).toBe('spreads: workflow list');
  });

  it('passes correct props to the navigation bar', function() {
    triggerLogRecord("ERROR");
    triggerLogRecord("ERROR");
    var navbar = TestUtils.findRenderedComponentWithType(app, NavigationBar);
    expect(navbar.props.title).toEqual(document.title);
    expect(navbar.props.numUnreadErrors).toEqual(2);
  });

  it('renders correct screen for route.', function() {
    expect(TestUtils.findRenderedComponentWithType(app, WorkflowList)).toBeDefined();
  });

  it('creates a new Workflow object before rendering with the WorkflowForm component', function() {
    app.props.view = "create";
    app.forceUpdate();
    expect(workflows.models.length).toBe(1);
  });

  describe('MessageArea', function() {
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

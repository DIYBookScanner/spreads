describe("Workflow", function() {
  var jQuery, workflows, dispatcher, _;
  beforeEach(function() {
    jest.dontMock('backbone');
    jest.dontMock('backbone-validation');
    jest.dontMock('../../vendor/backbone-deep-model.js');
    jest.dontMock('../workflow.js');
    jQuery = require('jquery');
    Backbone = require('backbone');
    Backbone.$ = jQuery;
    var Workflows = require('../workflow.js');
    _ = require('underscore');
    // Needed for Backbone.sync
    dispatcher = _.clone(require('backbone').Events);
    window.pluginTemplates = require('../../testutils/fixtures.js').templates;
    workflows = new Workflows();
  });

  it("sets default configuration from templates on initialization", function() {
    var workflow = new workflows.model(),
        config = workflow.get('config');
        expect(_.keys(config)).toEqual(["device", "test_output",
                                        "test_process", "test_process2"]);
        expect(config.test_output.selectable).toBe("a");
        expect(config.test_process.float).toBe(3.14);
  });

  it("sets up validators for configuration options from templates on initialization", function() {
    var workflow = new workflows.model(),
        validators = workflow.validation;
    expect(validators['config.test_output.selectable'].oneOf).toEqual(["a", "b", "c"]);
    expect(validators['config.test_process.float'].pattern).toBe("number");
  });

  it("correctly catches validation errors", function() {
    var workflow = new workflows.model(),
        config = workflow.get('config');
    // Slash in workflow name
    workflow.set('name', "foo/bar");
    expect(_.has(workflow.validate(), 'name')).toBe(true);
    // String in number config option
    config.test_process.float = "string";
    workflow.set('config', config);
    expect(_.has(workflow.validate(), 'config.test_process.float')).toBe(true);
    // Invalid value for selectable
    config.test_output.selectable = "d";
    workflow.set('config', config);
    expect(_.has(workflow.validate(), 'config.test_output.selectable')).toBe(true);
  });

  describe("Backend Communication", function() {
    var workflow, jqPromise = {fail: jest.genMockFn(),
                               done: jest.genMockFn(),
                               complete: jest.genMockFn()};
    jqPromise.fail.mockReturnValue(jqPromise)
    jqPromise.done.mockReturnValue(jqPromise)
    jqPromise.complete.mockReturnValue(jqPromise)

    beforeEach(function() {
      workflow = new workflows.model();
      workflow.set('id', 1);
      workflow.set('name', 'backend_test');
      workflow.set('images', []);
      workflows.add(workflow);
      jQuery.post.mockReturnValue(jqPromise);
    }),

    it("creates new workflow on the backend", function() {
      var newWorkflow = new workflows.model({'name': "foobar"});
      workflows.add(newWorkflow);
      newWorkflow.save();
      expect(jQuery.ajax.mock.calls.length).toBe(1);
      expect(jQuery.ajax.mock.calls.slice(-1)[0][0].url).toBe('/api/workflow');
      expect(jQuery.ajax.mock.calls.slice(-1)[0][0].type).toBe('POST');
    });

    it("updates existing workflow on the backend", function() {
      workflow.set({'config.test_process.float': 5.8});
      workflow.save();
      expect(jQuery.ajax.mock.calls.length).toBe(1);
      expect(jQuery.ajax.mock.calls.slice(-1)[0][0].url).toBe('/api/workflow/1');
      expect(jQuery.ajax.mock.calls.slice(-1)[0][0].type).toBe('PUT');
    });

    it("sends 'submit' request to backend", function() {
      var cb = jest.genMockFn();
      workflow.set('id', 1);
      workflow.submit(cb);
      expect(jQuery.post.mock.calls.length).toBe(1);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/submit');
    });

    it("sends 'transfer' request to backend", function() {
      var cb = jest.genMockFn();
      workflow.set('id', 1);
      workflow.transfer(cb);
      expect(jQuery.post.mock.calls.length).toBe(1);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/transfer');
    });

    it("sends 'prepare_capture' request to backend", function() {
      var cb = jest.genMockFn();
      workflow.set('id', 1);
      // Regular
      workflow.prepareCapture(cb);
      expect(jQuery.post.mock.calls.length).toBe(1);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/prepare_capture');
      // With reset
      workflow.prepareCapture(cb, true);
      expect(jQuery.post.mock.calls.length).toBe(2);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/prepare_capture?reset=true');
    });

    it("sends 'capture' request to backend", function() {
      var cb = jest.genMockFn(),
          eventFn = jest.genMockFn();
      workflow.set('id', 1);
      workflow.on('change:images', eventFn);
      workflow.triggerCapture(false, cb);
      expect(jQuery.post.mock.calls.length).toBe(1);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/capture');
      jQuery.post.mock.calls.slice(-1)[0][1/*success callback*/]({images: ['foo.jpg', 'bar.jpg']});
      expect(eventFn.mock.calls.length).toBe(1);
      expect(eventFn).lastCalledWith(['foo.jpg', 'bar.jpg']);

      // With retake option
      workflow.triggerCapture(true, cb);
      expect(jQuery.post.mock.calls.length).toBe(2);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/capture?retake=true');
      jQuery.post.mock.calls.slice(-1)[0][1/*success callback*/]({images: ['foo.jpg', 'bar.jpg']});
      expect(eventFn.mock.calls.length).toBe(2);
      expect(eventFn).lastCalledWith(['foo.jpg', 'bar.jpg']);
    });

    it("sends 'finish_capture' request to backend", function() {
      workflow.finishCapture(null);
      expect(jQuery.post.mock.calls.length).toBe(1);
      expect(jQuery.post.mock.calls.slice(-1)[0][0]).toBe('/api/workflow/1/finish_capture');
    });
  });

  describe("Events", function() {
    it('connects all events', function() {
      var mockDispatcher = {on: jest.genMockFn()};
      workflows.connectEvents(mockDispatcher);
      expect(mockDispatcher.on.mock.calls.length).toBe(4);
      expect(mockDispatcher.on.mock.calls[0][0/*event name*/]).toBe("workflow:created");
      expect(mockDispatcher.on.mock.calls[1][0/*event name*/]).toBe("workflow:removed");
      expect(mockDispatcher.on.mock.calls[2][0/*event name*/]).toBe("workflow:capture-triggered");
      expect(mockDispatcher.on.mock.calls[3][0/*event name*/]).toBe("workflow:capture-succeeded");
    });

    it('adds a workflow on "workflow:created"', function() {
      var testWorkflow = {
        id: 1,
        name: 'test'
      };
      workflows.connectEvents(dispatcher);
      dispatcher.trigger('workflow:created', testWorkflow);
      expect(workflows.get(1)).toBeDefined();
      expect(workflows.get(1).get('name')).toBe('test');
    });

    it('removes the right workflow on "workflow:removed"', function() {
      var dummyWorkflows = [
        {id: 1, name: 'foo'},
        {id: 2, name: 'bar'}
      ];
      workflows.connectEvents(dispatcher);
      workflows.add(dummyWorkflows);
      dispatcher.trigger('workflow:removed', {id: 2});
      expect(workflows.models.length).toBe(1);
      expect(workflows.get(2)).toBeUndefined();
      expect(workflows.get(1)).toBeDefined();
    });

    it('proxies workflow:capture-triggered to the right workflow', function() {
      workflows.connectEvents(dispatcher);
      workflows.add({id: 1, name: 'foo'});
      var modelObj = workflows.get(1),
          eventFn = jest.genMockFn();
      modelObj.on('capture-triggered', eventFn);
      dispatcher.trigger('workflow:capture-triggered', {id: 1});
      expect(eventFn.mock.calls.length).toBe(1);
    });

    it('adds images on workflow:capture-succeeded to the right workflow', function() {
      workflows.connectEvents(dispatcher);
      workflows.add({id: 1, name: 'foo', images: []});
      var modelObj = workflows.get(1),
          eventFn = jest.genMockFn();
      modelObj.on('capture-succeeded', eventFn);
      dispatcher.trigger('workflow:capture-succeeded',
                         {id: 1, images: ['foo.jpg', 'bar.jpg']});
      expect(eventFn.mock.calls.length).toBe(1);
      expect(modelObj.get('images')).toEqual(['foo.jpg', 'bar.jpg']);
    });

    it('sends events when individual configuration options are changed', function() {
      var workflow = new workflows.model(),
          eventFn = jest.genMockFn();
      workflow.on('change:config.test_output.selectable', eventFn);
      workflow.set({
        'config.test_output.selectable': 'b'
      });
      expect(eventFn.mock.calls.length).toBe(1);
    });
  });
});

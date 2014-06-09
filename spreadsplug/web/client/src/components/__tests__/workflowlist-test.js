describe("WorkflowList", function() {
  var workflows, WorkflowList, ReactTestUtils, util, mediaCallback;

  beforeEach(function() {
    jest.dontMock('../../workflow.js');
    jest.dontMock('../workflowlist.js');
    var _ = require('underscore'),
        Backbone = require('backbone');
    window.router = { events: _.clone(Backbone.Events)};
    window.matchMedia = jest.genMockFn().mockReturnValue(
      {addListener: function(fn) {mediaCallback = fn}});
    WorkflowList = require('../workflowlist.js');
    ReactTestUtils = require('react/addons').addons.TestUtils;
    util = require('../../../testutils/util.js');
    var Workflows = require('../../workflow.js'),
        workflow;
    require('../../util.js').isSmall.mockReturnValue(false);
    workflows = new Workflows();
    workflow = new workflows.model();
    workflow.set({id: 1, slug: 'foo', name: 'foo', raw_images: ['001', '002'],
                  status: {step: null, step_progress: null, prepared: false}});
    workflows.add(workflow);
  });

  it("displays help message when no workflows are present", function() {
    var Workflows = require('../../workflow.js'),
        list = WorkflowList({workflows: new Workflows()}),
        rows;
    ReactTestUtils.renderIntoDocument(list);
    expect(ReactTestUtils.findRenderedDOMComponentWithTag(list, 'h2')).toBeDefined();
  });

  it("displays workflows", function() {
    window.config = { web: {mode: 'full'}};
    var list = WorkflowList({workflows: workflows});
    ReactTestUtils.renderIntoDocument(list);
    var wfItems = util.findComponentsByDisplayName(list, 'WorkflowItem');
    expect(wfItems.length).toBe(1);
  });

  it("updates when workflows are added", function() {
    window.config = { web: {mode: 'full'}};
    var list = WorkflowList({workflows: workflows});
    ReactTestUtils.renderIntoDocument(list);
    var wfItems = util.findComponentsByDisplayName(list, 'WorkflowItem');
    expect(wfItems.length).toBe(1);
    var newWf = new workflows.model();
    newWf.set({id: 2, slug: 'bar', name: 'bar', raw_images: ['001', '002'],
               status: {step: null, step_progress: null, prepared: false}});
    workflows.add(newWf);
    wfItems = util.findComponentsByDisplayName(list, 'WorkflowItem');
    expect(wfItems.length).toBe(2);
  });

  describe("WorkflowItem", function() {
    var itemComponent;

    beforeEach(function() {
      window.config = { web: {mode: 'full', standalone_device: true}};
      var list = ReactTestUtils.renderIntoDocument(WorkflowList({workflows: workflows}));
      itemComponent = util.findComponentsByDisplayName(list, "WorkflowItem")[0];
    });

    it("renders links to workflow details", function() {
      var detailLinks = util.findComponentsByProps(itemComponent,
                                                   {href: '/workflow/foo'});
      expect(detailLinks.length).toBe(2);
    });

    it("shows the correct metadata", function() {
      expect(ReactTestUtils.scryRenderedDOMComponentsWithTag(itemComponent, 'p')[0].props.children)
             .toEqual([2, " pages"]);
    });

    it("shows second-to-last image as preview thumbnail", function() {
      expect(ReactTestUtils.scryRenderedDOMComponentsWithTag(itemComponent, 'img')[0].props.src)
             .toEqual("001/thumb");
    });

    it("shows placeholder when no images are on the workflow", function() {
      workflows.get(1).set('raw_images', []);
      expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(itemComponent, 'columns')[0].props.children)
             .toEqual("no images");
    });

    xit("shows information about postprocessing progress", function() {
    });

    xit("shows information about output progress", function() {
    });

    describe("Workflow removal", function() {
      var OkModal;

      beforeEach(function() {
        OkModal = require('../foundation.js').confirmModal;
        var removeButton = ReactTestUtils.findRenderedDOMComponentWithClass(itemComponent, 'fi-trash');
        ReactTestUtils.Simulate.click(removeButton.getDOMNode());
      });

      it("displays a confirmation modal when a workflow is to be removed", function() {
        expect(ReactTestUtils.findRenderedComponentWithType(itemComponent, OkModal)).toBeDefined();
      });

      it("removes the workflow and closes the modal when the action is confirmed", function() {
        var modal = ReactTestUtils.findRenderedComponentWithType(itemComponent, OkModal),
            jQuery = require('jquery');
        require('backbone').$ = jQuery;
        modal.props.onConfirm();
        expect(jQuery.ajax.mock.calls.length).toBe(1);
        expect(jQuery.ajax.mock.calls.slice(-1)[0][0].url).toBe('/api/workflow/1');
        expect(jQuery.ajax.mock.calls.slice(-1)[0][0].type).toBe('DELETE');
        jQuery.ajax.mock.calls.slice(-1)[0][0].success();
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, OkModal).length).toBe(0);
        expect(workflows.length).toBe(0);
      });

      it("closes the modal when the action is canceled", function() {
        var modal = ReactTestUtils.findRenderedComponentWithType(itemComponent, OkModal);
        modal.props.onCancel();
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, OkModal).length).toBe(0);
        expect(workflows.length).toBe(1);
      });
    });

    describe("Workflow download", function() {
      var removeButton, ActivityOverlay;

      beforeEach(function() {
        ActivityOverlay = require('../overlays.js').Activity;
        var dlButton = ReactTestUtils.findRenderedDOMComponentWithClass(itemComponent, 'fi-download');
        ReactTestUtils.Simulate.click(dlButton.getDOMNode());
      });

      it("displays activity overlay while download is prepared", function() {
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, ActivityOverlay).length).toBe(1);
      });

      it("closes activity overlay when download is finished preparing", function() {
        window.router.events.trigger('download:prepared');
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, ActivityOverlay).length).toBe(0);
      });

      it("blocks removal of the workflow while download is in progress", function() {
        var removeButton = ReactTestUtils.findRenderedDOMComponentWithClass(itemComponent, 'fi-trash');
        expect(removeButton.props.onClick).toBe(null);
        expect(removeButton.props.className).toContain('disabled');
      });

      it("re-enables removal when download is finished", function() {
        var removeButton = ReactTestUtils.findRenderedDOMComponentWithClass(itemComponent, 'fi-trash');
        window.router.events.trigger('download:finished');
        expect(removeButton.props.onClick).not.toBe(null);
        expect(removeButton.props.className).not.toContain('disabled');
      });
    });

    describe("Workflow transfer", function() {
      var ProgressOverlay;

      beforeEach(function() {
        ProgressOverlay = require('../overlays.js').Progress;
        workflows.get(1).transfer = jest.genMockFn();
        var transButton = ReactTestUtils.findRenderedDOMComponentWithClass(itemComponent, 'fi-usb');
        ReactTestUtils.Simulate.click(transButton.getDOMNode());
      });

      it("displays a progress overlay when a transfer is in progress", function() {
        // Trigger success callback
        workflows.get(1).transfer.mock.calls[0][0](null, 'success');
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, ProgressOverlay).length).toBe(1);
        var overlay = ReactTestUtils.findRenderedComponentWithType(itemComponent, ProgressOverlay);
        expect(overlay.props.statusMessage).toBe("Preparing transfer...");
      });

      it("updates progress overlay when progress events are fired", function() {
        // Trigger success callback
        workflows.get(1).transfer.mock.calls[0][0](null, 'success');
        window.router.events.trigger('transfer:progressed', {progress: 0.5, status: "foobar"});
        var overlay = ReactTestUtils.findRenderedComponentWithType(itemComponent, ProgressOverlay);
        expect(overlay.props.progress).toBe(50);
        expect(overlay.props.statusMessage).toBe("foobar");
      });

      it("closes progress overlay when transfer is finished", function() {
        // Trigger success callback
        workflows.get(1).transfer.mock.calls[0][0](null, 'success');
        window.router.events.trigger('transfer:completed');
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, ProgressOverlay).length).toBe(0);
      });

      it("displays an error dialog when an error occured during transfer", function() {
        // Trigger failure callback
        workflows.get(1).transfer.mock.calls[0][0]({responseJSON: {error: "Some error"}},
                                                   'error');
        var Modal = require('../foundation.js').modal;
        expect(ReactTestUtils.scryRenderedComponentsWithType(itemComponent, Modal).length).toBe(1);
        var modal = ReactTestUtils.findRenderedComponentWithType(itemComponent, Modal);
        expect(modal.props.fixed).toBe(true);
        expect(modal.props.children[0].props.children).toEqual("Transfer failed");
        expect(modal.props.children[1].props.children).toEqual("Some error");
      });
    });

    describe("ActionBar", function() {
      it("becomes a dropdown menu on small displays", function() {
        var mqMock = {matches: false};
        mediaCallback(mqMock);
        var barComponent = util.findComponentsByDisplayName(itemComponent, "ActionBar")[0];
        expect(barComponent.props.smallDisplay).toBe(true);
        var column = ReactTestUtils.findRenderedDOMComponentWithClass(barComponent, "columns");
        expect(column.props.children[0]).not.toBe(false);
        expect(column.props.children[0].props.className).toContain('dropdown');
        var toggleBtn = column.props.children[0];
        ReactTestUtils.Simulate.click(toggleBtn.getDOMNode());
        expect(column.props.children[1]).not.toBe(false);
        ReactTestUtils.Simulate.click(toggleBtn.getDOMNode());
        expect(column.props.children[1]).toBe(false);
      });

      it("hides the capture button when running in postprocessing mode", function() {
        window.config.web.mode = "processor";
        var barComponent = util.findComponentsByDisplayName(itemComponent, "ActionBar")[0];
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-camera").length).toBe(0);
        window.config.web.mode = "scanner";
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-camera").length).toBe(1);
      });

      it("only displays the transfer button when the standalone option is set", function() {
        window.config.web.standalone_device = true;
        var barComponent = util.findComponentsByDisplayName(itemComponent, "ActionBar")[0];
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-usb").length).toBe(1);
        window.config.web.standalone_device = false;
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-usb").length).toBe(0);
      });

      it("only displays the submission button when running in scanner mode", function() {
        window.config.web.mode = "scanner";
        var barComponent = util.findComponentsByDisplayName(itemComponent, "ActionBar")[0];
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-cloud").length).toBe(1);
        window.config.web.mode = "full";
        barComponent.forceUpdate();
        expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(barComponent, "fi-cloud").length).toBe(0);
      });
    });
  });
});

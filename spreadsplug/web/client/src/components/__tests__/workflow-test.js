describe("WorkflowDisplay", function() {
  var WorkflowDetails, ReactTestUtils, util, workflow, view;

  beforeEach(function() {
    jest.dontMock('../../workflow.js');
    jest.dontMock('../workflow.js');
    WorkflowDetails = require('../workflow.js');
    ReactTestUtils = require('react/addons').addons.TestUtils;
    util = require('../../../testutils/util.js');
    var Workflows = require('../../workflow.js');
    workflows = new Workflows();
    workflow = new workflows.model();
    // TODO: Force pagination by making raw_images.length > 24
    workflow.set({id: 1, slug: 'foo', name: 'foo', raw_images: ['001', '002'],
                  config: {plugins: ["test1", "test2"]},
                  status: {step: 'capture', step_progress: null, prepared: true}});
    workflows.add(workflow);
    view = ReactTestUtils.renderIntoDocument(WorkflowDetails({workflow: workflow}));
  });

  it("displays correct workflow metadata", function() {
    var heading = ReactTestUtils.findRenderedDOMComponentWithTag(view, 'h1');
    expect(heading).toBeDefined();
    expect(heading.props.children).toEqual('foo');
    var metalist = ReactTestUtils.scryRenderedDOMComponentsWithTag(view, 'ul')[0];
    expect(metalist.props.children[0].props.children)
          .toEqual("capture");
    expect(metalist.props.children[1].props.children.join(''))
          .toEqual("Enabled plugins: test1, test2");
  });

  it("displays grid of thumbnails", function() {
    var grid = ReactTestUtils.findRenderedDOMComponentWithClass(view, 'small-block-grid-2');
    expect(grid).toBeDefined();
    expect(grid.props.children.length).toBe(2);
    var preview = grid.props.children[0];
    expect(ReactTestUtils.findRenderedDOMComponentWithTag(preview, 'img')
                         .getDOMNode().src).toMatch(/.*001\/thumb$/);
  });

  it("updates grid when page is changed", function() {
  });

  it("doesn't display grid when there are no images", function() {
    workflow.set('raw_images', []);
    var grid = ReactTestUtils.findRenderedDOMComponentWithClass(view, 'small-block-grid-2');
    expect(grid.props.children.length).toBe(0);
  });

  it("toggle selection when a thumbnail is clicked", function() {
    var preview = ReactTestUtils.scryRenderedDOMComponentsWithClass(view, 'page-preview')[0];
    ReactTestUtils.Simulate.click(preview.props.children[0].getDOMNode());
    expect(preview.props.className).toEqual("th page-preview selected");
  });

  it("displays list of output files, if present", function() {
    expect(view.refs.outputlist).not.toBeDefined();
    workflow.set('output_files', ["foo.pdf", "foo.html"]);
    view.forceUpdate();
    var heading = ReactTestUtils.scryRenderedDOMComponentsWithTag(view, 'h2')[2];
    expect(heading.props.children).toEqual("Output files");
    expect(view.refs.outputlist).toBeDefined();
    expect(view.refs.outputlist.props.children.length).toBe(2);
    expect(view.refs.outputlist.props.children[0].props.key).toEqual("foo.pdf");
  });

  it("displays a zoom icon when a thumbnail is hovered", function() {
    var preview = ReactTestUtils.scryRenderedDOMComponentsWithClass(view, 'page-preview')[0];
    // NOTE: This does not work
    //ReactTestUtils.Simulate.mouseEnter(preview.getDOMNode());
    preview.props.onMouseEnter();
    expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(preview, 'toggle-zoom').length).toBe(1);
  });

  it("always displays a zoom icon on touch-devices", function() {
    require('../../util.js').isTouchDevice.mockReturnValue(true);
    view = ReactTestUtils.renderIntoDocument(WorkflowDetails({workflow: workflow}));
    var preview = ReactTestUtils.scryRenderedDOMComponentsWithClass(view, 'page-preview')[0];
    expect(ReactTestUtils.scryRenderedDOMComponentsWithClass(preview, 'toggle-zoom').length).toBe(1);
  });

  it("displays a lightbox when a zoom icon is clicked", function() {
    var preview = ReactTestUtils.scryRenderedDOMComponentsWithClass(view, 'page-preview')[0];
    expect(preview.isMounted()).toBe(true);
    preview.props.onMouseEnter();
    var zoomBtn = ReactTestUtils.findRenderedDOMComponentWithClass(preview, 'toggle-zoom');
    //workflow.deleteImage = jest.genMockFn();
    ReactTestUtils.Simulate.click(zoomBtn);
    var lightbox = util.findComponentsByDisplayName(view, 'LightBox')[0];
    expect(lightbox).toBeDefined();
    expect(lightbox.props.src).toEqual('001');
   // expect(workflow.deleteImage).toBeCalled();
  });
});

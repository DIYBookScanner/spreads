var ReactTestUtils = require('react/addons').addons.TestUtils;

module.exports = {
  findComponentsByDisplayName: function findComponentsByDisplayName(tree, displayName) {
    return ReactTestUtils.findAllInRenderedTree(tree, function(component) {
      return component.type.displayName === displayName;
    });
  },
  findComponentsByProps: function findComponentsByProps(tree, props) {
    return ReactTestUtils.findAllInRenderedTree(tree, function(component) {
      for (var key in props) {
        if (component.props[key] != props[key]) {
          return false;
        }
      }
      return true;
    });
  }
}

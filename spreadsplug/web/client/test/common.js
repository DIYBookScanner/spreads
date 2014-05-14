require('./phantomjs-shims.js');

var _ = require('underscore'),
    Backbone = require('backbone'),
    EventDispatcher = require('../src/events.js'),
    MockRouter, MockConfiguration, MockTemplates,  mockSocket, mockServer;

mockSocket = {
  triggerEvent: function(name, data) {
    this.onmessage({data: JSON.stringify({ name: name, data: data})});
  }
}

MockRouter = _.extend({}, Backbone.Events);

MockConfiguration = {
  web: {
    standalone_device: true
  }
}

MockTemplates = {
  "device": {
    "flip_target_pages": {
      "advanced": false,
      "docstring": "Temporarily switch target pages(useful for e.g. East-Asian books",
      "selectable": false,
      "value": false
    },
    "parallel_capture": {
      "advanced": false,
      "docstring": "Trigger capture on multiple devices at once.",
      "selectable": false,
      "value": true
    }
  },
  "test_output": {
    "selectable": {
      "advanced": false,
      "docstring": "A selectable",
      "selectable": true,
      "value": ["a", "b", "c"]
    },
    "string": {
      "advanced": false,
      "docstring": "A string",
      "selectable": false,
      "value": "moo"
    }
  },
  "test_process": {
    "a_boolean": {
      "advanced": false,
      "docstring": "A boolean",
      "selectable": false,
      "value": true
    },
    "float": {
      "advanced": false,
      "docstring": "A float",
      "selectable": false,
      "value": 3.14
    }
  },
  "test_process2": {
    "an_integer": {
      "advanced": false,
      "docstring": "An integer", 
      "selectable": false,
      "value": 10
    },
    "list": {
      "advanced": false,
      "docstring": "A list",
      "selectable": false,
      "value": [1, 2, 3]
    }
  }
}

beforeEach(function() {
  spyOn(window, "WebSocket").and.returnValue(mockSocket);
  jasmine.Ajax.install();
  window.router = MockRouter;
  window.router.events = new EventDispatcher();
  mockSocket.onopen()
  window.config = MockConfiguration;
  window.pluginTemplates = MockTemplates;
});

afterEach(function() {
  jasmine.Ajax.uninstall()
  delete window.router;
  delete window.config;
  delete window.pluginTemplates;
});

module.exports = {
  configuration: {
    web: {
      standalone_device: true
    }
  },
  templates: {
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
}

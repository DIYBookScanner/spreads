var EventDispatcher = require('../../src/events.js');

describe('EventDispatcher', function() {
  var dispatcher;

  beforeEach(function() {
    dispatcher = new EventDispatcher();
  });

  it("opens a WebSocket connection if available", function() {
    var socket = window.WebSocket();
    expect(socket.onopen).toBeDefined();
    expect(socket.onclose).toBeDefined();
    expect(socket.onmessage).toBeDefined();
  });

  it("correctly formats workflow events", function() {
    var eventFn = jasmine.createSpy("success");
    dispatcher.on('workflow:1337:removed', eventFn);
    dispatcher.emitEvent({name: 'workflow:removed', data: {id: 1337}});
    expect(eventFn).toHaveBeenCalledWith({});
  });

  it("falls back to long polling if the WebSocket connection fails", function() {
    var pollDispatcher, originalWS, dummyEvent,
        eventFn = jasmine.createSpy("success");

    dummyEvent = {
      "level": "INFO",
      "message": "An informational message",
      "origin": "Workflow",
      "time": 1400006863.413,
      "traceback": null
    };

    originalWS = window.WebSocket;
    window.WebSocket = false;
    pollDispatcher = new EventDispatcher();
    pollDispatcher.on('logrecord', eventFn);
    expect(jasmine.Ajax.requests.mostRecent().url).toBe('/api/poll');
    jasmine.Ajax.requests.mostRecent().response({
      "status": 200,
      "contentType": "application/json",
      "responseText": JSON.stringify([{
        "data": dummyEvent,
        "name": "logrecord"
      }])
    });
    expect(eventFn).toHaveBeenCalledWith(dummyEvent);
    window.WebSocket = originalWS;
  });
});

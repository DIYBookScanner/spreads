describe('SomeTest', function() {
  var EventDispatcher;

  beforeEach(function(){
    jest.dontMock('../events.js');
    EventDispatcher = require('../events.js');
  });

  it("opens a WebSocket connection if available", function() {
    var socket = {},
        eventFn = jest.genMockFn(),
        dispatcher;
    window.WebSocket = jasmine.createSpy().andReturn(socket);
    dispatcher = new EventDispatcher();
    expect(socket.onopen).toBeDefined();
    expect(socket.onclose).toBeDefined();
    socket.onopen();
    expect(socket.onmessage).toBeDefined();
    dispatcher.on('test', eventFn);
    socket.onmessage({data: JSON.stringify({name: 'test',
                                            data: {'it': 'works'}})});
    expect(eventFn).lastCalledWith({'it': 'works'});
  });

  describe("LongPolling", function() {
    var jQuery, pollDispatcher;
    beforeEach(function() {
      window.WebSocket = false;
      jQuery = require('jquery');
      pollDispatcher = new EventDispatcher();
    });

    it("is used if WebSockets are not supported", function() {
      expect(jQuery.ajax.mock.calls.length).toBe(1);
      expect(jQuery.ajax.mock.calls[0][0].url).toEqual('/api/poll');
    });

    it("is used if the WebSocket connection fails to establish", function() {
      var failSocket = {};
      window.WebSocket = jasmine.createSpy().andReturn(failSocket);
      pollDispatcher = new EventDispatcher();
      failSocket.onclose();
      // two since there was one already in the `beforeEach`
      expect(jQuery.ajax.mock.calls.length).toBe(2);
    });

    it("correctly dispatches events", function() {
      var eventFn = jest.genMockFn();
      pollDispatcher.on('logrecord', eventFn);
      jQuery.ajax.mock.calls.slice(-1)[0/*last call*/][0/*first argument*/].success(
        [{name: 'logrecord', data: {'foo': 'bar'}}]);
      expect(eventFn).lastCalledWith({'foo': 'bar'});
    });

    it("resumes polling after a response or timeout", function() {
      jQuery.ajax.mock.calls.slice(-1)[0/*last call*/][0/*first argument*/]
        .complete(null, "timeout");
      jQuery.ajax.mock.calls.slice(-1)[0/*last call*/][0/*first argument*/]
        .complete(null, "success");
      expect(jQuery.ajax.mock.calls.length).toBe(3);
    });

    it("waits 30 seconds after a failed connection attempt before resuming", function() {
      jQuery.ajax.mock.calls.slice(-1)[0/*last call*/][0/*first argument*/]
        .complete(null, "error");
      expect(jQuery.ajax.mock.calls.length).toBe(1);
      expect(setTimeout.mock.calls.length).toBe(1);
      expect(setTimeout.mock.calls[0][1]).toBe(30*1000);
      jest.runAllTimers();
      expect(jQuery.ajax.mock.calls.length).toBe(2);
    });
  });
});

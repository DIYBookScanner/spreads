'use strict';

angular.module('spreads').service('StatusService', function() {
    // TODO: Obtain values from API
    this.currentStep = "setup";
    this.stepNum = 0;
    this.messages = [];
    this.configuration = {};
    //this.start_time
    //this.shot_count
});

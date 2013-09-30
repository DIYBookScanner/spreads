/* global angular, console */
'use(strict)';

angular.module('spreads').service('StatusService', function() {
    // TODO: Obtain values from API
    this.currentStep = 'setup';
    this.stepNum = 0;
    this.messages = [];
    //this.start_time
    //this.shot_count
});

angular.module('spreads').service('ConfigService', function($http) {
    var config = this;
    console.debug('Getting values from server');
    $http.get('/api/configuration').success(function(data) {
        for (var sectionKey in data) {
            if (data.hasOwnProperty(sectionKey)) {
                var section = data[sectionKey];
                config[sectionKey] = {};
                for (var key in section) {
                    if (section.hasOwnProperty(key)) {
                        config[sectionKey][key] = section[key];
                    }
                }
            }
        }
    });
});

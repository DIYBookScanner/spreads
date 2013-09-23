'use strict';

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
    $http.get('/api/configuration/template').success(function(data) {
        for (var sectionKey in data) {
            if (data.hasOwnProperty(sectionKey)) {
                var template = data[sectionKey];
                config[sectionKey] = {};
                for (var key in template) {
                    if (template.hasOwnProperty(key)) {
                        var option = template[key];
                        if (typeof(option.value) === "object") {
                            config[sectionKey][key] = option.value[0];
                        } else {
                            config[sectionKey][key] = option.value;
                        }
                    }
                }
            }
        }
    });
});


'use strict';

angular.module('spreads', []).
    config(['$routeProvider', function($routeProvider) {
        $routeProvider.
            when('/setup', {templateUrl: 'partials/setup.html', controller: SetupCtrl}).
            when('/scan', {templateUrl: 'partials/scan.html', controller: ScanCtrl}).
            when('/download', {templateUrl: 'partials/download.html', controller: DownloadCtrl}).
            when('/verify', {templateUrl: 'partials/verify.html', controller: VerifyCtrl}).
            when('/submit', {templateUrl: 'partials/submit.html', controller: SubmitCtrl}).
            otherwise({templateUrl: 'partials/start.html', controller: StartCtrl});
}]);

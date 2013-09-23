/* jshint unused: false */
'use(strict)';

function ConfigCtrl($scope, $http, ConfigService) {
    $scope.configuration = ConfigService;
    $scope.submit = function() {
        // ConfigService.submit()
        console.debug("Sending configuration to server");
    }
}

function StatusCtrl($scope, StatusService) {
    $scope.status = StatusService;
}

function StartCtrl($scope, StatusService, $log, $location) {
    $log.info('Trying to redirect to /' + StatusService.currentStep);
    $location.path('/' + StatusService.currentStep);
}

function SetupCtrl($scope, StatusService, $log, $location) {
    StatusService.currentStep = 'setup';
    StatusService.stepNum = 1;

    $scope.next = function() {
        console.debug("Sending configuration to server");
        // ConfigService.submit()
        $location.path('/scan');
    };
}

function ScanCtrl($scope, StatusService, $log, $location) {
    StatusService.currentStep = 'scan';
    StatusService.stepNum = 2;
    $log.info('StatusService.stepNum is: ' + StatusService.stepNum);

    $scope.next = function() {
        $location.path('/download');
    };
}

function DownloadCtrl($scope, StatusService, $log, $location) {
    StatusService.currentStep = 'download';
    StatusService.stepNum = 3;

    $scope.next = function() {
        $location.path('/verify');
    };
}

function VerifyCtrl($scope, StatusService, $log, $location) {
    StatusService.currentStep = 'verify';
    StatusService.stepNum = 4;

    $scope.next = function() {
        $location.path('/submit');
    };
}

function SubmitCtrl($scope, StatusService, $log, $location) {
    StatusService.currentStep = 'submit';
    StatusService.stepNum = 5;
    $scope.next = function() {
        $location.path('/setup');
    };
}

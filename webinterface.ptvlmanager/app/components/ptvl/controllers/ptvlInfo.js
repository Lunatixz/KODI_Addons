define(['./ptvl'], function (ptvlControllers) {
    'use strict';

    ptvlControllers.controller('ptvlInfoCtrl', ['$scope', 'settingsList', function ($scope, settingsList) {

        settingsList.async().then(function (d) {
            $scope.settings = d;
        });

    }]);
});
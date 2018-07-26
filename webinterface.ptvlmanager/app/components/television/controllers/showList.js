define(['./television'], function (televisionControllers) {
    'use strict';

    televisionControllers.controller('showListCtrl', ['$scope', 'showList', function ($scope, showList) {

        showList.async().then(function (d) {
            $scope.shows = d;
        });


    }]);
});
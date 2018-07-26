define(['.././ptvl'], function (ptvlControllers) {
    'use strict';

    function uniqueStudios(origArr) {
        var newArr = [],
            origLen = origArr.length,
            found, x, y;

        for (x = 0; x < origLen; x++) {
            found = undefined;
            for (y = 0; y < newArr.length; y++) {
                if (origArr[x].name === newArr[y].name) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                newArr.push(origArr[x]);
            }
        }
        return newArr;
    }

    ptvlControllers.controller('tvStudioCtrl', ["$scope", 'lockFactory', function ($scope, lockFactory) {

        $scope.studios = [];

        $scope.studio = {};

        $scope.changed = {};
        $scope.changes = {};

        console.log($scope.shows);
        for(var studio in $scope.shows) {
            $scope.studios[studio] =
            {
                id: studio,
                name: $scope.shows[studio].studio[0]
            }
        }

        $scope.studios = uniqueStudios($scope.studios);

        $scope.studio.name = $scope.channel.rules.main[1];

        $scope.selectStudio = function (studio) {
            if($scope.studio.name !== studio.name) {
                $scope.changed.studio = true;
                $scope.changes.studio = studio;
            }
            console.log(studio);
            console.log($scope.channel);
        };

        $scope.undoStudio = function () {
            var r = confirm("Are you sure you want to undo changing the studio?");
            if(r == true) {
                $scope.changed.studio = false;
                $scope.studio.selected = $scope.studio;
            }

        };

        $scope.saveStudio = function () {
            alert("Don't forget to download your new settings2.xml at the bottom!");
            $scope.channel.rules.main[1] = $scope.changes.studio.name;
            $scope.changed.studio = false;
            console.log($scope.channel);
            $scope.channel.locked = lockFactory.toggleLock($scope.channel.channel);
        }


    }]);
});
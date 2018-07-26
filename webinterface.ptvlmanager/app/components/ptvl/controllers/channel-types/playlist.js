define(['.././ptvl'], function (ptvlControllers) {
    'use strict';

    ptvlControllers.controller('playlistDetailsCtrl', ['$scope', 'playlistList', function ($scope, playlistList) {

        var type = 'video';

        $scope.playlists = [];

        $scope.playlist = {};

        playlistList.async(type).then(function (d) {
            $scope.videoPlaylists = d;
            for(var label in $scope.videoPlaylists) {
                $scope.playlists[label] =
                {
                    id: label,
                    name: $scope.videoPlaylists[label].label
                };
            }
        });

    }]);
});
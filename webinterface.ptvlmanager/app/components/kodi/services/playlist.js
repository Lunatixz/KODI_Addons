define(['./kodi'], function (kodiServices) {
    'use strict';

    kodiServices.factory('playlistList', ['$http', function ($http) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var VideoListReq = JSON.stringify({
            "jsonrpc": "2.0",
            "method": "Files.GetDirectory",
            "params": {
                "directory": "special://profile/playlists/video",
                "media": "files"
            },
            "id": "PTVLM"
        });

        var playlistList = {
            async: function (type) {
                if(type = 'video') {
                    var ListReq = VideoListReq;
                }
                else{

                }
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + ListReq).then(function (response) {

                    // The return value gets picked up by the then in the controller.
                    return response.data.result.files;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return playlistList;
    }]);
});
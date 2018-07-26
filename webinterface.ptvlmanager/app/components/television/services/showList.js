define(['./television'], function (televisonServices) {
    'use strict';

    televisonServices.factory('showList', ['$http', '$location', function ($http, $location) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var showListReq = JSON.stringify({
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": [
                    "title",
                    "genre",
                    "year",
                    "playcount",
                    "studio"
                ],
                "sort": {
                    "order": "ascending",
                    "ignorearticle": false,
                    "method": "sorttitle"
                }
            },
            "id": "PTVLM"
        });


        var showList = {
            async: function () {
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + showListReq).then(function (response) {
                    // The return value gets picked up by the then in the controller.
                    return response.data.result.tvshows;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return showList;
    }]);
});
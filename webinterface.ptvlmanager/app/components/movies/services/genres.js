define(['./movies'], function (moviesServices) {
    'use strict';

    moviesServices.factory('genreList', ['$http', function ($http) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var genreListReq = JSON.stringify({
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetMovies",
            "params": {
                "properties": [
                    "title",
                    "year",
                    "playcount",
                    "set"
                ],
                "sort": {
                    "order": "ascending",
                    "ignorearticle": false,
                    "method": "sorttitle"
                }
            },
            "id": "PTVLM"
        });


        var moviesList = {
            async: function () {
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + genreListReq).then(function (response) {
                    console.log(response.data.results);
                    // The return value gets picked up by the then in the controller.
                    return response.data.results;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return moviesList;
    }]);
});
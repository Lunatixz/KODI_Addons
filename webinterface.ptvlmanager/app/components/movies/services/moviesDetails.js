define(['./movies'], function (moviesServices) {
    'use strict';

    moviesServices.factory('moviesDetails', ['$http', function ($http) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var moviesDetails = {
            async: function (movieid) {

                var movieDetailsReq = JSON.stringify({
                    "jsonrpc": "2.0",
                    "method": "VideoLibrary.GetMovieDetails",
                    "id": 1,
                    "params": [
                        movieid,
                        [
                            "title",
                            "genre",
                            "year",
                            "tagline",
                            "originaltitle",
                            "lastplayed",
                            "playcount",
                            "runtime",
                            "thumbnail",
                            "file",
                            "sorttitle",
                            "resume",
                            "fanart",
                            "dateadded",
                            "rating",
                            "director",
                            "trailer",
                            "plot",
                            "plotoutline",
                            "writer",
                            "studio",
                            "mpaa",
                            "cast",
                            "country",
                            "imdbnumber",
                            "set",
                            "showlink",
                            "streamdetails",
                            "top250",
                            "votes",
                            "setid",
                            "tag",
                            "art"
                        ]
                    ]
                });

                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + movieDetailsReq).then(function (response) {
                    console.log(response.data.result.moviedetails);
                    // The return value gets picked up by the then in the controller.
                    return response.data.result.moviedetails;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return moviesDetails;
    }]);
});
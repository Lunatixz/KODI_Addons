define(['./television'], function (televisionServices) {
    'use strict';

    televisionServices.factory('showDetails', ['$http', '$location', function ($http, $location) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var showDetails = {
            async: function (tvshowid) {

                var showDetailsReq = JSON.stringify({
                    "jsonrpc": "2.0",
                    "method": "VideoLibrary.GetTVShowDetails",
                    "id": 1,
                    "params": [
                        tvshowid,
                        [
                            "title",
                            "genre",
                            "year",
                            "thumbnail",
                            "plot",
                            "cast",
                            "art"
                        ]
                    ]
                });

                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + showDetailsReq).then(function (response) {
                    console.log(response.data.result.tvshowdetails);
                    // The return value gets picked up by the then in the controller.
                    return response.data.result.tvshowdetails;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return showDetails;
    }]);
});
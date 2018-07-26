define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.factory('rssFactory', ['$http', function ($http) {



        var rssFactory = {
            async: function () {
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get("https://raw.githubusercontent.com/Lunatixz/PseudoTV_Lists/master/rss.xml").then(function (response) {
                    // The return value gets picked up by the then in the controller.
                    return response.data;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return rssFactory;
    }]);

});
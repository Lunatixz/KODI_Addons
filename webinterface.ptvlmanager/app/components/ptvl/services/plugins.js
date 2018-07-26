define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.factory('pluginList', ['$http', '$location', function ($http, $location) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var pluginListReq = JSON.stringify({
            "jsonrpc": "2.0",
            "method": "Addons.GetAddons",
            "params":
            {
                "type": "xbmc.addon.video"
            },
            "id": "PTVLM"
        });


        var pluginList = {
            async: function () {
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + pluginListReq).then(function (response) {

                    // The return value gets picked up by the then in the controller.
                    return response.data.result.addons;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return pluginList;
    }]);
});
define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.factory('settingsList', ['$http', '$location', function ($http, $location) {

        var protocol = window.location.protocol;
        var host = window.location.host;

        var url = protocol+ '//' + host + '/jsonrpc?request=';

        var settingsListReq = JSON.stringify({
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "params": [
                "script.pseudotv.live",
                [
                    "name",
                    "version",
                    "summary",
                    "description",
                    "path",
                    "author",
                    "thumbnail",
                    "fanart",
                    "dependencies"
                ]
            ],
            "id": "PTVLM"
        });


        var settingsList = {
            async: function () {
                // $http returns a promise, which has a then function, which also returns a promise
                var promise = $http.get(url + settingsListReq).then(function (response) {
                    console.log(response.data.result.addon);
                    // The return value gets picked up by the then in the controller.
                    return response.data.result.addon;
                });
                // Return the promise to the controller
                return promise;
            }
        };
        return settingsList;
    }]);
});
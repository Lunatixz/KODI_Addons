define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.service('dialogService', ['$state', '$timeout', 'dialogs', function($state, $timeout, dialogs) {

        var confirmed = true;

        var _progress = 1;

        var _fakeWaitProgress = function(){
            $timeout(function(){
                if(_progress < 100){
                    _progress += 33;
                    dialogs.wait("Please wait", "Just a few more chickens to count", _progress);
                    _fakeWaitProgress();
                }else{
                    dialogs.wait.complete = true;
                    _progress = 0;
                }
            },1000);
        };

        return {
            confirm: function (params) {
                var header = params.header;
                var body = params.body;
                var state = params.state;
                var dlg = dialogs.confirm(header, body);
                dlg.result.then(function(btn){
                    confirmed = true;
                },function(btn){
                    confirmed = false;
                    if (state != null) {
                        $state.go(state);
                    }
                });
                return confirmed;
            }
        }
    }]);
});
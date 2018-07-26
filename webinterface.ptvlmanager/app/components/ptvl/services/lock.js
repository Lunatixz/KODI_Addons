define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.factory('lockFactory', [function () {

        var locked = [];

        return {
            addLock: function (value) {
                console.log(value);
                locked.push(value);
            },
            getLocked: function (value) {
                for(var i=0; i<locked.length; i++) {
                    if(locked[i].channel === value)
                    {
                        console.log('Channel '+value+' is locked? '+locked[i].locked);
                        return locked[i].locked;
                    }
                }
            },
            toggleLock: function (value) {
                for(var i=0; i<locked.length; i++) {
                    if(locked[i].channel === value)
                    {
                        locked[i].locked = !locked[i].locked;
                        return locked[i].locked;
                    }
                }
            }
        }

    }]);
});
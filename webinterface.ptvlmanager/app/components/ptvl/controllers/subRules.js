define(['./ptvl'], function (ptvlControllers) {
    'use strict';

    function ObjectLength( object ) {
        var length = 0;
        for( var key in object ) {
            if( object.hasOwnProperty(key) ) {
                ++length;
            }
        }
        return length;
    };

    ptvlControllers.controller('subRulesCtrl', ['$scope', 'ruleFactory', function ($scope, ruleFactory) {

        $scope.subsLocked = true;

        if(isNaN($scope.channel.channel)) {

        }
        else {
            $scope.rules = ruleFactory.getSubRules($scope.channel.rules);

            if (typeof($scope.rules[13].value.options[1]) !== 'undefined') {
                $scope.rules[13].value.options[1] = parseInt($scope.rules[13].value.options[1]) / 60;
            }
        }

        $scope.wip = true;

        $scope.unlockSubs = function () {
            $scope.subsLocked = false;
        };

        $scope.saveSubRules = function () {

            $scope.rules.length = ObjectLength($scope.rules);

            $scope.rules.enabled = 0;

            $scope.rules[13].value.options[1] = parseInt($scope.rules[13].value.options[1]) * 60;

            var s = 0;

            for(var i=1; i<$scope.rules.length; i++) {

                if($scope.rules[i].status === true) {
                    $scope.rules.enabled++;

                    s++;
                    console.log(i);
                    if(typeof($scope.channel.rules.sub[s]) !== 'undefined')
                    {
                        console.log('This one is true!', $scope.rules[i]);
                        console.log($scope.channel.rules.sub[s]);
                        $scope.channel.rules.sub[s].id = $scope.rules[i].id.toString();
                        $scope.channel.rules.sub[s].options = jQuery.extend(true, {}, $scope.rules[i].value.options);
                    }
                    else
                    {
                        $scope.channel.rules.sub[s] = {};
                        console.log('This one is true! ELSE', $scope.rules[i]);
                        $scope.channel.rules.sub[s].id = $scope.rules[i].id.toString();
                        $scope.channel.rules.sub[s].options = jQuery.extend(true, {}, $scope.rules[i].value.options);
                    }
                }

                console.log($scope.channel);
            }
            console.log($scope.rules);
            $scope.channel.rules.count = $scope.rules.enabled;
            $scope.subsLocked = true;
        };

    }]);
});
define(['./ptvl'], function (ptvlControllers) {
    'use strict';

    ptvlControllers.controller('typeCtrl', ['$scope', '$templateCache', 'lockFactory', 'ruleFactory', function ($scope, $templateCache, lockFactory, ruleFactory) {

        var chTempPath = 'app/components/ptvl/templates/channel-types/';

        var typeTemps = ['directory', 'playlist', 'plugin', 'rss', 'tv-genre', 'tv-studio', 'youtube'];

        for(var i=0; i<typeTemps.length; i++) {
            $templateCache.get(chTempPath+typeTemps[i]+'.html');
        }

        $templateCache.get('app/components/ptvl/templates/channel-details/sort-limit.html');
        $templateCache.get('app/components/ptvl/templates/channel-details/sub-rules.html');

        var channelLocked = 
        {
            channel: $scope.channel.channel,
            locked: true
        };

        lockFactory.addLock(channelLocked);

        $scope.channel.locked = lockFactory.getLocked($scope.channel.channel);

        $scope.channelLocked = 'Unlock';

        $scope.types = ruleFactory.getTypes();

        $scope.type = {};

        $scope.changed =
        {
            type: false,
            saved: true
        };

        $scope.changes = {};

        $scope.lock = function (channel)
        {
            if($scope.channel.locked)
            {
                var r = confirm("Are you sure you want to "+$scope.channelLocked.toLowerCase()+" channel "+ channel.channel +"?");
                if(r == true) {
                    $scope.channelLocked = 'Lock';
                    $scope.channel.locked = lockFactory.toggleLock($scope.channel.channel);
                }
            }
            else if(!$scope.channel.locked)
            {
                var r = confirm("Are you sure you want to "+$scope.channelLocked.toLowerCase()+" channel "+ channel.channel);
                if(r == true) {
                    $scope.channelLocked = 'Unlock';
                    $scope.channel.locked = lockFactory.toggleLock($scope.channel.channel);
                }
            }
        };

        $scope.channel.type = ruleFactory.getType($scope.channel.type);
        console.log($scope.channel.type);


        // When a new type is selected, add to $scope.changes
        $scope.selectType = function (type) {
            if($scope.channel.type.name == type.name) {
                if($scope.changed.type == true) {
                    $scope.channel.type.templateUrl = $scope.channel.type.oldTemplateUrl;
                    delete $scope.channel.type['oldTemplateUrl'];
                }
                $scope.changed.type = false;
                $scope.changed.saved = true;
                console.log(type);
                console.log($scope.channel.type);
            }
            else {
                $scope.channel.type.oldTemplateUrl = $scope.channel.type.templateUrl;
                $scope.channel.type.templateUrl = type.templateUrl;
                console.log($scope.channel.type);
                $scope.changes.type = type;
                $scope.changed.type = true;
                $scope.changed.saved = false;
            }
        };

        $scope.undo = function () {
            var r = confirm("Are you sure you want to change the type back to "+$scope.channel.type.name+"?");
            if (r == true) {
                $scope.type.selected = $scope.channel.type;
                $scope.channel.type.templateUrl = $scope.channel.type.oldTemplateUrl;
                delete $scope.channel.type['oldTemplateUrl'];
                console.log($scope.channel.type);
                $scope.changed.type = false;
                $scope.changed.saved = true;
            }
        };

        $scope.saveType = function () {
            var r = confirm("Are you sure you want to change the type to "+$scope.changes.type.name+"?");
            if (r == true){
                alert("Don't forget to download your new settings2.xml at the bottom!");
                $scope.channel.type.value = $scope.changes.type.value;
                $scope.channel.changed = 'True';
                delete $scope.channel['type'];
                console.log($scope.channel);
                $scope.changed.saved = true;
                $scope.changed.type = false;
                $scope.channel.locked = lockFactory.toggleLock($scope.channel.channel);
                $scope.channelLocked = 'Unlock';
            }
        };

    }]);
});
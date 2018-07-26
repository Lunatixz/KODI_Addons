define(['.././ptvl'], function (ptvlControllers) {
    'use strict';

    
    ptvlControllers.controller('youtubeDetailsCtrl', ['$scope', 'ruleFactory', function ($scope, ruleFactory) {

        $scope.changed =
        {
            value: false,
            path: false,
            YtType: false,
            sort: false,
            limit: false
        };

        $scope.YtTypes = ruleFactory.getYtTypes();

        // Adds the Sort options available to the scope, for the ui-select drop down
        $scope.sorts = ruleFactory.getSorts();

        // Adds the Limits options available to the scope, for the ui-select drop down
        $scope.limits = ruleFactory.getLimits();

        $scope.changes = {};

        // Adds a YtType object for attaching the selection
        $scope.YtType = {};

        console.log($scope.channel.type);
        console.log($scope.channel.rules.main[2]);
        if($scope.channel.type.value == 10) {
            // Binds the specific type the channel uses to the YtType object
            $scope.YtType = ruleFactory.getYtType($scope.channel.rules.main[2]);

            // Adds a sort object for attaching the selection
            $scope.sort = ruleFactory.getSort($scope.channel.rules.main[4]);

            // Adds a limit object for attaching the selection
            $scope.limit = ruleFactory.getLimit($scope.channel.rules.main[3]);

            // Creates a value for mapping the YouTube type to the input label
            $scope.input = $scope.YtType.name;

            // Creates a value for mapping the path (Username, Playlist, etc.)
            $scope.path = $scope.channel.rules.main[1];
        }
        else{
            $scope.YtType = $scope.YtTypes[0];
            $scope.input = $scope.YtType.name;
            $scope.sort = $scope.sorts[0];
            $scope.limit = $scope.limits[0];
            $scope.path = '';
        }

        // When a YouTube type is selected, backup the old type, clear the old type, and set it to the selected one
        $scope.selectYtType = function (YtType)
        {
            if($scope.YtType.name !== YtType.name)
            {
                $scope.changed.YtType = true;
                $scope.changes.YtType = YtType.value;
                $scope.path = '';
                console.log('YouTube Type changed to '+YtType.name);
                $scope.input = YtType.name;
            }
            else
            {
                alert('We must have missed something!!');
            }
        };

        // Go back to the originally loaded type
        $scope.undoYtType = function ()
        {
            var r = confirm("Are you sure you want to undo changing the YouTube Type?");
            if(r == true) {
                $scope.changed.YtType = false;
                $scope.YtType.selected = $scope.YtType;
                $scope.input = $scope.YtType.name;
            }
        };

        $scope.selectSort = function (sort)
        {
            if(parseInt($scope.channel.rules.main[4]) !== sort.value) {
                $scope.changed.sort = true;
                $scope.changed.value = true;
                $scope.changes.sort = sort.value;
            }
            else {
                $scope.changed.sort = false;
                $scope.changed.value = false;
            }

        };

        $scope.undoSort = function ()
        {
            var r = confirm("Are you sure you want to undo changing the youtube sort?");
            if(r == true) {
                $scope.changed.sort = false;
                $scope.changed.value = false;
                $scope.sort.selected = $scope.sort;
            }
        };

        $scope.selectLimit = function (limit)
        {
            if(parseInt($scope.channel.rules.main[3]) !== limit.value) {
                $scope.changed.limit = true;
                $scope.changed.value = true;
                $scope.changes.limit = limit.value;
            }
            else {
                $scope.changed.limit = false;
                $scope.changed.value = false;
            }

        };

        $scope.undoLimit = function ()
        {
            var r = confirm("Are you sure you want to undo changing the youtube limit?");
            if(r == true) {
                $scope.changed.limit = false;
                $scope.changed.value = false;
                $scope.limit.selected = $scope.limit;
            }
        };

        $scope.changedPath = function ()
        {
            $scope.changed.path = true;
            $scope.changed.value = true;
        };

        $scope.saveYouTube = function (channel, path)
        {
            channel.rules.main[1] = path;
            if (typeof $scope.changes.limit != 'undefined')
            {
                channel.rules.main[3] = $scope.changes.limit;
            }
            if (typeof $scope.changes.sort != 'undefined')
            {
                channel.rules.main[4] = $scope.changes.sort;
            }

            for ( var key in $scope.changed ) {
                $scope.changed[key] = false;
            }
        };

    }]);
});
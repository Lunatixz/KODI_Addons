define(['.././ptvl'], function (ptvlControllers) {
    'use strict';

    ptvlControllers.controller('rssDetailsCtrl', ['$scope', 'ruleFactory', 'rssFactory', function ($scope, ruleFactory, rssFactory) {

        $scope.isCollapsed = true;

        $scope.rssCommunityFeeds = [];

        rssFactory.async().then(function (d) {
            console.log(d);

            d = d.split('\n');
            console.log(d);

            for(var i = 0; i<d.length; i++) {
                d[i] = d[i].split(',');
                if(d[i][0].contains('http')) {
                    $scope.rssCommunityFeeds[i] = {
                        'name': d[i][1],
                        'feed': d[i][0]
                    }
                }
            };
            console.log($scope.rssCommunityFeeds);
        });

        $scope.rssCommunityFeeds.selected = {};

        $scope.changed =
        {
            value: false,
            path: false,
            sort: false,
            limit: false
        };

        // Adds the Sort options available to the scope, for the ui-select drop down
        $scope.sorts = ruleFactory.getSorts();

        // Adds the Limits options available to the scope, for the ui-select drop down
        $scope.limits = ruleFactory.getLimits();

        $scope.changes = {};

        console.log($scope.channel.type);
        if($scope.channel.type.value == 11) {

            // Adds a sort object for attaching the selection
            $scope.sort = ruleFactory.getSort($scope.channel.rules.main[4]);

            // Adds a limit object for attaching the selection
            $scope.limit = ruleFactory.getLimit($scope.channel.rules.main[3]);

            // Creates a value for mapping the path (Username, Playlist, etc.)
            $scope.path = $scope.channel.rules.main[1];
        }
        else{
            $scope.input = $scope.YtType.name;
            $scope.sort = $scope.sorts[0];
            $scope.limit = $scope.limits[0];
            $scope.path = '';
        }

        // When a YouTube type is selected, backup the old type, clear the old type, and set it to the selected one
        $scope.selectRssFeed = function (rss)
        {
            $scope.pathBackup = $scope.path;
            $scope.changed.value = true;
            $scope.changed.path = true;
            $scope.path = rss.feed;
        };

        // Go back to the originally loaded type
        $scope.undoRssFeed = function ()
        {
            var r = confirm("Are you sure you want to undo changing the YouTube Type?");
            if(r == true) {
                $scope.changed.value = false;
                $scope.changed.path = false;
                $scope.path = $scope.pathBackup;
                $scope.rssCommunityFeeds.selected.name = 'None';

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
            var r = confirm("Are you sure you want to undo changing the plugin sort?");
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
            var r = confirm("Are you sure you want to undo changing the rss limit?");
            if(r == true) {
                $scope.changed.limit = false;
                $scope.changed.value = false;
                $scope.limit.selected = $scope.limit;
            }
        };

        $scope.saveRss = function (channel, path)
        {
            var r = confirm("Would you like to name the channel to the community name?");
            if(r == true) {
                channel.rules.sub[1].id = "1";
                channel.rules.sub[1].options[1] = $scope.rssCommunityFeeds.selected.name;
            }

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
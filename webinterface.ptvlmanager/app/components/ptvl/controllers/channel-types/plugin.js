define(['.././ptvl'], function (ptvlControllers) {
    'use strict';

    ptvlControllers.controller('pluginDetailsCtrl', ['$scope', 'pluginList', 'ruleFactory', function ($scope, pluginList, ruleFactory) {

        pluginList.async().then(function (d) {
            $scope.plugins = d;
        });

        $scope.changed =
        {
            value: false,
            subfolders: false,
            plugin: false,
            sort: false,
            limit: false
        };

        // Adds the Sort options available to the scope, for the ui-select drop down
        $scope.sorts = ruleFactory.getSorts();

        // Adds the Limits options available to the scope, for the ui-select drop down
        $scope.limits = ruleFactory.getLimits();

        $scope.changes = {};

        $scope.plugin ={};

        if($scope.channel.type.value == 15) {
            $scope.sort = ruleFactory.getSort($scope.channel.rules.main[4]);
            $scope.limit = ruleFactory.getLimit($scope.channel.rules.main[3]);
            $scope.channel = ruleFactory.getPluginParts($scope.channel);
            $scope.plugin.addonid = $scope.channel.plugin.addonid;
            $scope.subfolders = $scope.channel.plugin.subfolders;
            console.log($scope.channel);
        }

        else {
            console.log("This is the channel: ", $scope.channel);
        }

        $scope.selectPlugin = function (plugin)
        {
            if($scope.plugin.addonid !== plugin.addonid)
            {
                $scope.changed.plugin = true;
                $scope.changes.addonid = plugin.addonid;
                $scope.subfolders = '';
                console.log('Addonid changed to '+$scope.changes.addonid+', but not yet applied!')
            }
            else
            {
                $scope.changed.plugin = false;
                $scope.subfolders = $scope.channel.plugin.subfolders;
            }
        };

        $scope.undoPlugin = function ()
        {
            var r = confirm("Are you sure you want to undo changing the plugin?");
            if(r == true) {
                $scope.changed.plugin = false;
                $scope.plugin.selected = $scope.plugin;
                $scope.subfolders = $scope.channel.plugin.subfolders;
            }
            else
            {
                $scope.changed.subfolders = true;
            }

        };

        $scope.changedSubs = function ()
        {
            $scope.changed.subfolders = true;
            $scope.changed.value = true;
        };

        $scope.undoSub = function ()
        {
            var r = confirm("Are you sure you want to undo changing the plugin subfolder path?");
            if(r == true) {
                $scope.subfolders = $scope.channel.plugin.subfolders;
            }
            else {
                $scope.subfolders = '';
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
                console.log(limit.value);
                $scope.changes.limit = limit.value;
            }
            else {
                $scope.changed.limit = false;
                $scope.changed.value = false;
            }

        };

        $scope.undoLimit = function ()
        {
            var r = confirm("Are you sure you want to undo changing the plugin sort?");
            if(r == true) {
                $scope.changed.limit = false;
                $scope.changed.value = false;
                $scope.limit.selected = $scope.limit;
            }
        };

        $scope.savePlugin = function (channel, subfolders)
        {
            channel.plugin.subpath = subfolders;
            channel.rules.main[1] = 'plugin://'+channel.plugin.addonid+'/'+channel.plugin.subpath;
            if (typeof $scope.changes.limit != 'undefined')
            {
                channel.rules.main[3] = $scope.changes.limit;
            }
            if (typeof $scope.changes.sort != 'undefined')
            {
                channel.rules.main[4] = $scope.changes.sort;
            }
            console.log(channel);
            for ( var key in $scope.changed ) {
                $scope.changed[key] = false;
            }
        };

    }]);
});
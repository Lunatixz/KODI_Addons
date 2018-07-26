define(['./ptvl'], function (ptvlServices) {
    'use strict';

    ptvlServices.factory('ruleFactory', [function () {

        var types = [
            {name: 'Playlist (WIP-4/28)',                     value: 0,   templateUrl: '/app/components/ptvl/templates/channel-types/playlist.html'},
            {name: 'TV Studio (WIP-4/28)',                    value: 1,   templateUrl: '/app/components/ptvl/templates/channel-types/tv-studio.html'},
            {name: 'Movie Studio (Not Started)',              value: 2},
            {name: 'TV Genre (Not Started)',                  value: 3,   templateUrl: '/app/components/ptvl/templates/channel-types/tv-genre.html'},
            {name: 'Movie Genre (Not Started)',               value: 4},
            {name: 'Mixed Genre (Not Started)(TV & Movie)',   value: 5},
            {name: 'TV Show (Not Started)',                   value: 6},
            {name: 'Directory (Not Started)',                 value: 7,   templateUrl: '/app/components/ptvl/templates/channel-types/directory.html'},
            {name: 'LiveTV (Not Started)',                    value: 8},
            {name: 'InternetTV (Not Started)',                value: 9},
            {name: 'YoutubeTV',                               value: 10,  templateUrl: '/app/components/ptvl/templates/channel-types/youtube.html'},
            {name: 'RSS (WIP-6/29)',                          value: 11,  templateUrl: '/app/components/ptvl/templates/channel-types/rss.html'},
            {name: 'Music (Not Started)',                     value: 12},
            {name: 'Music Videos (Not Started)',              value: 13},
            {name: 'Extras (Not Started)',                    value: 14},
            {name: 'Plugin',                                  value: 15,  templateUrl: '/app/components/ptvl/templates/channel-types/plugin.html'},
            {name: 'Playon (Not Started)',                    value: 16},
            {name: 'Global Settings (Not Started)',           value: 99,  templateUrl: '/app/components/ptvl/templates/channel-types/plugin.html'}
        ];

        var subRules = [
            {name: 'Nothing',                   id: 0,   status: false, value: {options: { 1: '' }}},
            {name: 'Name',                      id: 1,   status: false, value: {options: { 1: '' }}},
            {name: 'Shows not to Play',         id: 2,   status: false, value: {options: {}}},
            {name: 'Best Efforts Scheduling',   id: 3,   status: false, value: {options: {}}},
            {name: 'Only play watched',         id: 4,   status: false, value: '4'},
            {name: "Don't show this channel",   id: 5,   status: false, value: '5'},
            {name: 'Interleaved Shows',         id: 6,   status: false, value: {options: {}}},
            {name: 'Play Real-Time Mode',       id: 7,   status: false, value: '7'},
            {name: 'Pause when not watching',   id: 8,   status: false, value: '8'},
            {name: 'Play Resume Mode',          id: 9,   status: false, value: '9'},
            {name: 'Play Random',               id: 10,  status: false, value: '10'},
            {name: 'Play Only Unwatched',       id: 11,  status: false, value: '11'},
            {name: 'Play Shows in Order',       id: 12,  status: false, value: '12'},
            {name: 'Reset Every X Hours',       id: 13,  status: false, value: {options: { 1: {} }}},
            {name: 'Exclude Strms',             id: 14,  status: false, value: {options: { 1: 'No' }}},
            {name: 'Show Logo',                 id: 15,  status: false, value: {options: { 1: 'Yes' }}},
            {name: 'Nothing',                   id: 16,  status: false, value: {options: { 1: '' }}},
            {name: 'Exclude BCT',               id: 17,  status: false, value: {options: { 1: 'No' }}},
            {name: 'Disable Popup',             id: 18,  status: false, value: {options: { 1: 'No' }}}
        ];

        var limits = [
            {limit: '25',   value: 25},
            {limit: '50',   value: 50},
            {limit: '100',  value: 100},
            {limit: '150',  value: 150},
            {limit: '200',  value: 200},
            {limit: '250',  value: 250},
            {limit: '500',  value: 500},
            {limit: '1000', value: 1000}
        ];

        var sorts = [
            {order: 'Default',  value: 0},
            {order: 'Random',   value: 1},
            {order: 'Reverse',  value: 2}
        ];

        var YtTypes = [
            {name: 'None',              value: 0},
            {name: 'Channel/User',      value: 1},
            {name: 'Playlist',          value: 2},
            {name: 'New Subs',          value: 3},
            {name: 'Favorites',         value: 4},
            {name: 'Search (Safe)',     value: 5},
            {name: 'Blank',             value: 6},
            {name: 'Multi Playlist',    value: 7},
            {name: 'Multi Channel',     value: 8},
            {name: 'Raw (Gdata)',       value: 9}
        ];

        return {
            getType: function (value) {
                for(var i=0; i<types.length; i++) {
                    if(types[i].value === parseInt(value))
                    {
                        return types[i];
                    }
                }
            },
            getSubRules: function (rules) {
                var chSubRules = jQuery.extend({}, subRules);
                for(var s=1; s <= rules.count; s++) {
                    for(var i=0; i<subRules.length; i++) {
                        if (subRules[i].id === parseInt(rules.sub[s].id)) {
                            if (rules.sub[s].options !== 'undefined') {
                                subRules[i].value.options = rules.sub[s].options;
                            }
                            chSubRules[i] = jQuery.extend(true, {}, subRules[i]);
                            chSubRules[i].status = true;
                        }
                    }
                }
                return chSubRules;
            },
            getLimits: function () {
              return limits;
            },
            getLimit: function (value) {
                for(var i=0; i<limits.length; i++) {
                    if(limits[i].value === parseInt(value))
                    {
                        return limits[i];
                    }
                }
            },
            getSorts: function () {
                return sorts;
            },
            getSort: function (value) {
                for(var i=0; i<sorts.length; i++) {
                    if(sorts[i].value === parseInt(value))
                    {
                        return sorts[i];
                    }
                }
            },
            getYtTypes: function () {
              return YtTypes;
            },
            getYtType: function (value) {
                for(var i=0; i<YtTypes.length; i++) {
                    if(YtTypes[i].name === value)
                    {
                        return YtTypes[i];
                    }
                }
            },
            getPluginParts: function (channel) {
                //cpsf = Count plugin subfolders
                var cpsf = channel.rules.main[1].split("/").length;
                channel.plugin = {};
                if (cpsf > 3)
                {
                    var myRegexp = /(plugin.video.*?\/)/g;
                    channel.plugin.addonid = myRegexp.exec(channel.rules.main[1]);

                    channel.plugin.addonid = channel.plugin.addonid[1].substring(0, channel.plugin.addonid[1].length -1);
                    channel.plugin.subfolders = channel.rules.main[1].split("/").splice(3, cpsf);
                    channel.plugin.pluginPath = "plugin://" + channel.plugin.addonid + "/" + channel.plugin.subfolders.join("/");
                    channel.plugin.subPath = channel.plugin.subfolders.join("/");
                    return channel;
                }
                // If there aren't any SubFolders "plugin://plugin.video.*"
                else
                {
                    myRegexp = /(plugin.video.*)/g;
                    channel.plugin.addonid = myRegexp.exec(channel.rules.main[1]);
                    channel.plugin.addonid = channel.plugin.addonid[1].substring(0, channel.plugin.addonid[1].length);
                    channel.plugin.pluginPath = "plugin://" + channel.plugin.addonid;
                    channel.plugin.subfolders = '';
                    return channel;
                }
            },
            getTypes: function () {
                return types;
            }

        }

    }]);
});
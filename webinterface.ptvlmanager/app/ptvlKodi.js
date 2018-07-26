define([
    'angular',
    'uiRouter',
    'uiBootstrap',
    'uiSortable',
    'uiTemplates',
    'uiSelect',
    'ngAria',
    'ngAnimate',
    'ngSanitize',
    'ngTouch',
    'blob',
    'x2js',
    'ngDialogs',
    './components/movies/services/index',
    './components/television/services/index',
    './components/movies/controllers/index',
    './components/television/controllers/index',
    './components/kodi/services/index',
    './components/kodi/controllers/index',
    './components/ptvl/directives/index',
    './components/ptvl/services/index',
    './components/ptvl/controllers/index'
], function (ng) {
    'use strict';

    return ng.module('ptvlKodi', [
        'ptvlKodi.moviesServices',
        'ptvlKodi.moviesControllers',
        'ptvlKodi.televisionServices',
        'ptvlKodi.televisionControllers',
        'ptvlKodi.ptvlDirectives',
        'ptvlKodi.ptvlServices',
        'ptvlKodi.ptvlControllers',
        'ui.router',
        'ui.bootstrap',
        'ui.select',
        'ui.sortable',
        'ngAria',
        'ngAnimate',
        'ngSanitize',
        'ngTouch'
    ]);
});




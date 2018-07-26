define(['./ptvlKodi'], function(ptvlKodi) {
    'use strict';
    return ptvlKodi.config(['$provide', '$stateProvider', '$urlRouterProvider','$sceDelegateProvider',
        function($provide, $stateProvider, $urlRouterProvider, $sceDelegateProvider){

        $provide.decorator('accordionDirective', function($delegate) {
            var directive = $delegate[0];
            directive.replace = true;
            return $delegate;
        });

        $urlRouterProvider.otherwise('/home');

        $stateProvider

            .state('home', {
                url: '/home',
                templateUrl: '/app/global/home.html'
            })

            .state('movies', {
                url: '/movies',
                templateUrl: 'app/components/movies/movies.html',
                controller: 'moviesListCtrl'
            })

            .state('movies.details', {
                url: '/details',
                parent: 'movies',
                templateUrl: '/app/components/movies/movies-details.html',
                controller: 'moviesDetailsCtrl'
            })

            .state('shows', {
                url: '/shows',
                templateUrl: 'app/components/television/shows.html',
                controller: 'showListCtrl'
            })

            .state('shows.details', {
                url: '/details',
                parent: 'shows',
                templateUrl: '/app/components/television/show-details.html',
                controller: 'showDetailsCtrl'
            })

            .state('ptvl', {
                url: '/ptvl',
                templateUrl: 'app/components/ptvl/ptvl.html',
                controller: 'channelCtrl'
            })

            .state('about', {
                url: '/about',
                templateUrl: 'app/components/ptvl/aboutPtvl.html',
                controller: 'ptvlInfoCtrl'
            });


        $sceDelegateProvider.resourceUrlWhitelist([
            'self',
            '*://www.youtube.com/**'
        ]);

    }]);
});
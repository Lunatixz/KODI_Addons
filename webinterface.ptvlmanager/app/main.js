require.config({

    paths: {
        'domReady': '../bower_components/requirejs-domready/domReady',
        'angular': '../bower_components/angular/angular',
        "uiRouter": "../bower_components/angular-ui-router/release/angular-ui-router",
        "uiBootstrap": "../bower_components/angular-bootstrap/ui-bootstrap.min",
        "uiSelect": "../bower_components/angular-ui-select/dist/select.min",
        "uiSortable": "../bower_components/angular-ui-sortable/sortable",
        "uiTemplates": "../bower_components/angular-bootstrap/ui-bootstrap-tpls",
        "ngAria": "../bower_components/angular-aria/angular-aria.min",
        "ngAnimate": "../bower_components/angular-animate/angular-animate.min",
        "ngSanitize": "../bower_components/angular-sanitize/angular-sanitize.min",
        "ngTouch": "../bower_components/angular-touch/angular-touch.min",
        "blob": "../bower_components/blob/Blob",
        "x2js": "../bower_components/x2js/xml2json.min",
        "ngDialogs": "../bower_components/angular-dialog-service/dialogs.min"
    },

    /**
     * for libs that either do not support AMD out of the box, or
     * require some fine tuning to dependency mgt'
     */
    shim: {
        'angular': {
            exports: 'angular'
        },
        'uiRouter':{
            deps: ['angular']
        },
        'uiBootstrap':{
            deps: ['angular']
        },
        'uiTemplates':{
            deps: ['angular', 'uiBootstrap']
        },
        'uiSelect':{
            deps: ['angular', 'uiBootstrap', 'uiTemplates']
        },
        'uiSortable':{
            deps: ['angular', 'uiBootstrap', 'uiTemplates']
        },
        'ngAria':{
            deps: ['angular']
        },
        'ngAnimate':{
            deps: ['angular']
        },
        'ngSanitize':{
            deps: ['angular']
        },
        'ngTouch':{
            deps: ['angular']
        },
        'x2js':{
            deps: ['angular']
        },
        'ngDialogs':{
            deps: ['angular']
        }

    },

    deps: [
        // kick start application... see bootstrap.js
        './bootstrap'
    ]
});
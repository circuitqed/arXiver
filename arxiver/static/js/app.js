/**
 * Created by dave on 3/28/14.
 */

var app = angular.module("app", [
    'ngRoute',
    'ui.bootstrap',
    'appControllers'
]);

app.config(['$routeProvider',
    function($routeProvider) {
        $routeProvider.
            when('/articles', {
                templateUrl: 'partials/article-list.html',
                controller: 'ArticleListCtrl'
            }).
            when('/article/:articleId', {
                templateUrl: 'partials/article-detail.html',
                controller: 'ArticleDetailCtrl'
            }).
            otherwise({
                redirectTo: '/articles'
            });
    }]);


// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
// http://plnkr.co/edit/kODSLa?p=info
app.factory('debounce', function($timeout, $q) {
  return function(func, wait, immediate) {
    var timeout;
    var deferred = $q.defer();
    return function() {
      var context = this, args = arguments;
      var later = function() {
        timeout = null;
        if(!immediate) {
          deferred.resolve(func.apply(context, args));
          deferred = $q.defer();
        }
      };
      var callNow = immediate && !timeout;
      if ( timeout ) {
        $timeout.cancel(timeout);
      }
      timeout = $timeout(later, wait);
      if (callNow) {
        deferred.resolve(func.apply(context,args));
        deferred = $q.defer();
      }
      return deferred.promise;
    };
  };
});
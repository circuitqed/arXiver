/**
 * Created by dave on 3/28/14.
 */

var arxiver = angular.module("arxiver", [
    'ngRoute',
    //'ui.bootstrap',
    'arxiverControllers'
]);

arxiver.config(['$routeProvider',
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
            when('/author/:authorId', {
                templateUrl: 'partials/author_detail.html',
                controller: 'AuthorDetailCtrl'
            }).
            when('/user/:userId', {
                templateUrl: 'partials/user_profile.html',
                controller: 'UserCtrl'
            }).
            when('/feed/:feedId', {
                templateUrl: 'partials/feed_detail.html',
                controller: 'FeedDetailCtrl'
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
arxiver.factory('debounce', function($timeout, $q) {
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
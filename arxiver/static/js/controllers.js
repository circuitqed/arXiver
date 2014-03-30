/**
 * Created by dave on 3/29/14.
 */

var appControllers = angular.module('appControllers', []);

appControllers.controller("ArticleListCtrl", ['$scope', '$http', 'debounce',
    function ($scope, $http, debounce) {

        $scope.articles = [];
        $scope.query = '';
        $scope.hovering = false;
        $scope.hover_article = {};

        $scope.doHover = function (article) {
            $scope.hovering = true;
            $scope.hover_article = article;
            console.log("hover");
        };

        $scope.doLeave = function () {
            $scope.hovering = false;
            $scope.hover_article = {};
        };

        $http.get("/api/category").success(function (data) {
            $scope.categories = data.objects;
        });

        //http://plnkr.co/edit/AcvnKq2KPDTgnGicWB0b?p=preview
        $scope.doSearch = debounce(function () {

            var q = {};
            q.filters = [
                {name: "title", op: "like", val: "%" + $scope.title_query + "%"}
            ];

            var fq = angular.toJson(q);
            console.log(fq);
            $http.get("/api/article", {params: {q: fq}}).success(function (data) {
                $scope.articles = data.objects;
            });
        }, 500, false);

    }]);

appControllers.controller("ArticleDetailCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        $http.get("/api/article/" + $routeParams.articleId).success(function (data) {
            $scope.article = data;
        });

    }]);

appControllers.controller("FeedDetailCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        $http.get("/api/article/" + $routeParams.articleId).success(function (data) {
            $scope.article = data;
        });

    }]);

appControllers.controller("AuthorDetailCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        $http.get("/api/article/" + $routeParams.articleId).success(function (data) {
            $scope.article = data;
        });

    }]);

appControllers.controller("UserCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        $http.get("/api/article/" + $routeParams.articleId).success(function (data) {
            $scope.article = data;
        });

    }]);
/**
 * Created by dave on 3/29/14.
 */

var arxiverControllers = angular.module('arxiverControllers', []);

arxiverControllers.controller("ArticleListCtrl", ['$scope', '$http', 'debounce',
    function ($scope, $http, debounce) {

        $scope.articles = [];
        $scope.query = '';
        $scope.hovering = false;
        $scope.hover_article = {};
        $scope.title_query = '';
        $scope.date_query = '';
        $scope.author_query = '';
        $scope.keyword_query = '';

        $scope.doHover = function (article) {
            $scope.hovering = true;
            $scope.hover_article = article;
        };

        $scope.doLeave = function () {
            $scope.hovering = false;
            $scope.hover_article = {};
        };

        //get user (hard code to 1 for now)
//        $http.get("/api/user/1").success(function (data) {
//            $scope.current_user = data;
//        });
//
//        $http.get("/api/category").success(function (data) {
//            $scope.categories = data.objects;
//        });

        //http://plnkr.co/edit/AcvnKq2KPDTgnGicWB0b?p=preview
        $scope.doSearch = debounce(function () {

            var q = {};
            q.filters = [];
            q.disjunction = false;
            if ($scope.title_query !== '') {
                q.filters.push({name: "title", op: "like", val: "%" + $scope.title_query + "%"});
            }
            if ($scope.author_query !== '') {
                q.filters.push({name: "authors", op: "any", val: {name: "lastname", op: "like", val: $scope.author_query}});
            }
//            if ($scope.category_query !=='') {
//                q.filters.push({name: "category.name", op: "like", val: $scope.category_query + "%"});
//            }
            if ($scope.date_query !== '') {
                q.filters.push({name: "created", op: "like", val: $scope.date_query + "%"});
                //q.filters.push({name: "updated", op: "like", val: $scope.date_query + "%"});
            }
            if ($scope.keyword_query !== '') {
                q.filters.push({name: "abstract", op: "like", val: "%" + $scope.keyword_query + "%"});
            }

            var fq = angular.toJson(q);
//            console.log(fq);
//            $http.get("/api2/article", {params: {q: fq}}).success(function (data) {
//                $scope.articles = data.objects;
//            });
            $http.get("/api2/articles", {params: {"title": $scope.title_query}}).success(function (data) {
                $scope.articles = data;
                console.log($scope.articles.length);
            });
        }, 500, false);

    }]);

arxiverControllers.controller("ArticleDetailCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        $http.get("/api2/articles/" + $routeParams.articleId).success(function (data) {
            $scope.article = data;
        });

    }]);

arxiverControllers.controller("FeedDetailCtrl", ['$scope', '$http', '$routeParams', 'debounce',
    function ($scope, $http, $routeParams, debounce) {
        $scope.newFeed = $routeParams.feedId == "new";
        $scope.feed_preview = {};
        $scope.emailOptions = [
            {name: "Daily", value: 0},
            {name: "Weekly", value: 1},
            {name: "Monthly", value: 2}
        ];

        if ($scope.newFeed) {
            $scope.feed = {};
            $scope.feed.authors = [];
            $scope.feed.keywords = [];
            $scope.feed.email_frequency = $scope.emailOptions[0];
        }

        $scope.new_author = "";
        $scope.author_preview = {};

        $scope.new_keyword = '';
        $scope.keyword_preview = {};

        $scope.doAuthorSearch = debounce(function () {
            var q = {};

            q.filters = [
                {name: "lastname", op: "like", val: $scope.new_author + "%", limit: 10}
            ];
            var fq = angular.toJson(q);
            console.log(fq);
            $http.get("/api/author", {params: {q: fq}}).success(function (data) {
                $scope.author_preview = data.objects;
            })
        }, 500, false);

        $scope.addAuthor = function () {
            if ($scope.feed.authors.indexOf($scope.new_author) === -1) {
                $scope.feed.authors.push($scope.new_author);
                $scope.new_author = '';
                $scope.author_preview = {};
            }
        };
        $scope.removeAuthor = function (author) {
            $scope.feed.authors.splice($scope.authors.indexOf(author), 1);
        };

        $scope.addKeyword = function () {
            if ($scope.feed.keywords.indexOf($scope.new_keyword) === -1) {
                $scope.feed.keywords.push($scope.new_keyword);
                $scope.new_keyword = '';
                $scope.keyword_preview = {};
            }
        };
        $scope.removeKeyword = function (keyword) {
            $scope.keywords.splice($scope.keywords.indexOf(keyword), 1);
        };

        $scope.doKeywordSearch = debounce(function () {
            var q = {};

            q.filters = [
                {name: "keyword", op: "like", val: $scope.new_keyword + "%", limit: 10}
            ];
            var fq = angular.toJson(q);
            console.log(fq);
            $http.get("/api/keyword", {params: {q: fq}}).success(function (data) {
                $scope.keyword_preview = data.objects;
            })
        }, 500, false);

        $scope.doFeedSearch = debounce(function () {
            var q = {};
            q.filters = []

            for (var a in $scope.feed.authors) {
                q.filters.push({name: "lastname", op: "like", val: a});
            }
            for (var k in $scope.feed.keywords) {
                q.filters.push({name: "keyword", op: "like", val: k});
            }

            var fq = angular.toJson(q);
            console.log(fq);
            $http.get("/api/article", {params: {q: fq}}).success(function (data) {
                $scope.feed_preview = data.objects;
            })
        }, 500, false);

    }]);

arxiverControllers.controller("AuthorDetailCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {
        var q = {};
        var fq;

        $http.get("/api2/author/" + $routeParams.authorId).success(function (data) {
            $scope.author = data.author;
            $scope.similar_authors = data.similar_authors;
        });
//
//        $http.get("/api/author/" + $routeParams.authorId + "/articles").success(function (data) {
//            $scope.articles = data;
//        });


    }]);

arxiverControllers.controller("UserCtrl", ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {

        //get user (hard code to 1 for now)
        $http.get("/api/user/1").success(function (data) {
            $scope.user = data;
        });

    }]);
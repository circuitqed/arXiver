/**
 * Created by dave on 4/1/14.
 */


angular.module('arxiver.services', [])
  .factory('arxiverAPIservice', function($http) {

    var arxiverAPI = {};

    arxiverAPI.autocompleteAuthorSearch = function (author_query) {
        return debounce(function() {
            var q = {};

            q.filters = [
                {name: "lastname", op: "like", val: author_query+"%", limit:10}
            ];
            var fq = angular.toJson(q);
            console.log(fq);
            return $http.get("/api/author", {params: {q: fq}})
        },500,false)
    };

    return arxiverAPI;
  });
/**
 * Created by dave on 4/9/14.
 */


//FeedForm functions
function removeField() {
    var table = $(this).closest('table');
    var row = $(this).closest('tr');
    var fieldname = $(this).closest('.DynamicTextFieldList').data('name');

    console.log(fieldname);
    row.fadeOut();
    row.remove();
    table.find('.removable-field-input').each(function (i, field) {
        //console.log(fieldname + '-' + i)
        $(field).attr('id', fieldname + '-' + i).attr('name', fieldname + '-' + i)
        $(field).attr('id', fieldname + '-' + i).attr('name', fieldname + '-' + i)
    });

}

function addField(event) {
    var dyntable = $(this).closest('.DynamicTextFieldList');
    var fieldname = dyntable.data('name');
    var numinputs = dyntable.find('.removable-field-row').length;
    var field = $(
            '<tr class="removable-field-row">\n' +
            '<td><input id="' + fieldname + '-' + numinputs + '" name="' + fieldname + '-' + numinputs + '" type="text" class="removable-field-input typeahead" value=""></td>\n' +
            '<td><button type="button" class="removable-field-button">&times;</button></td>\n</tr>'
    );
    console.log(numinputs)
    event.preventDefault();
    $(this).closest('tr').before(field);
    bindTypeAhead();

}

function bindTypeAhead() {
    $('.author-typeahead').typeahead({
        hint: true,
        highlight: true,
        minLength: 1
    }, {
        name: 'author',
        displayKey: function (author) {
            return author.forenames + ' ' + author.lastname;
        },
        source: function (query, process) {
            console.log('typeahead');
            return $.get('/autocomplete/author/' + query, function (data) {
                process(data.authors);
            });
        }
    });
}


function bindKeywordTypeAhead() {
    $('.keyword-typeahead').typeahead({
        hint: true,
        highlight: true,
        minLength: 1
    }, {
        name: 'keyword',
        displayKey: function (keyword) {
            return keyword.keyword;
        },
        source: function (query, process) {
            console.log('typeahead');
            return $.get('/autocomplete/keyword/' + query, function (data) {
                process(data.keywords);
            });
        }
    });
}

function setupEditFeed() {
    $('a[data-remove-author]').click(function (event) {
        //$(this).hide();
        $(this).closest('span').hide();
        $.ajax({
            type: 'POST',
            url: '/delete_feed_author',
            data: JSON.stringify({author_id: $(this).attr('data-author_id'), feed_id: $(this).attr('data-feed_id')}),
            dataType: 'json',
            contentType: "application/json; charset=utf-8",

            complete: function () {
                //window.location.reload(); //reload the page on submit
            }

        });
        //event.preventDefault();
    });

    $('a[data-remove-keyword]').click(function (event) {
        //$(this).hide();
        $(this).closest('span').hide();
        $.ajax({
            type: 'POST',
            url: '/delete_feed_keyword',
            data: JSON.stringify({keyword: $(this).attr('data-keyword'), feed_id: $(this).attr('data-feed_id') }),
            dataType: 'json',
            contentType: "application/json; charset=utf-8",

            complete: function () {
                //window.location.reload(); //reload the page on submit
            }

        });
        //event.preventDefault();
    });

    $('a[data-add-keyword]').click(function (event) {
        var s = $($(this).attr('data-text')).val();
        $.ajax({
            type: 'POST',
            url: '/add_feed_keyword',
            data: JSON.stringify({keyword: s, feed_id: $(this).attr('data-feed_id') }),
            dataType: 'json',
            contentType: "application/json; charset=utf-8",

            complete: function () {
                console.log('success!')
                //window.location.reload(); //reload the page on submit
            }

        });
        //event.preventDefault();
    });

    $('#openBtn').click(function () {
        var s = $($(this).attr('data-text')).val();
        console.log(s);
        $('#myModalLabel').html('Edit: ' + s + ' feed status');
        $('.modal-body').load('/add_feed_author', {'query': s, 'feed_id': $(this).attr('data-feed_id'), 'endpoint': $(this).attr('href')}, function (result) {
            console.log(result)

            $('#myModal').modal();
        });
        event.preventDefault();

    });

    if ($('#enable_email').attr('checked')) {
        $('#email_frequency').show();
    }
    $('#enable_email').on('change', function () {
        $('#email_frequency').fadeToggle();
    });

}

function setupAuthor() {
    $('#followAuthorBtn').click(function () {
        $('#myModalLabel').html('Follow/Unfollow: ' + $(this).attr('data-author-names') + ' feed status');
        $('.modal-body').load('/add_feed_author', {'author_id': $(this).attr('data-author-id'), 'endpoint': $(this).attr('href')}, function (result) {
            //console.log(result)
            $('#myModal').modal();
        });
        event.preventDefault();

    });
}

$(document).ready(function () {
    //Bind Index events
    bindTypeAhead();

    //Bind FeedForm events
//    $('.DynamicTextFieldList').on('click', '.removable-field-button', removeField)
//        .on('click', '.addable-field-button', addField)
//    console.log($('email_frequency').attr('checked'))

    $('form[data-async]').on('submit', function (event) {
        var $form = $(this);
        //var $target = $($form.attr('data-target'));

        $.ajax({
            type: $form.attr('method'),
            url: $form.attr('action'),
            data: $form.serialize(),

            success: function () {
            },

            complete: function () {
                window.location.replace($form.attr('data-next'));
            }
        });

        event.preventDefault();
    });

    $('.slideDownCtl').click(function () {
        $($(this).attr('data-target')).slideToggle();
        event.preventDefault();
    });

    setupEditFeed();
    setupAuthor();
    bindKeywordTypeAhead();

});
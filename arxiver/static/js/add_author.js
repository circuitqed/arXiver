/**
 * Created by dave on 5/28/14.
 */


//Setup Add Author dialog

$('.btn-toggle').hover(
    function () {
        //$('.preview').show();
        $(".preview").filter("[data-previewid=" + $(this).attr("data-previewid") + "]").slideDown();
    },
    function () {
        $(".preview").filter("[data-previewid=" + $(this).attr("data-previewid") + "]").hide();
    }
);

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


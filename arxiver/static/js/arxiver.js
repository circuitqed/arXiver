/**
 * Created by dave on 4/9/14.
 */

function removeField() {
    $(this).closest('tr').fadeOut();
    var fieldname = $(this).closest('.DynamicTextFieldList').data('name')
    console.log('remove')
    $(this).closest('table').find('.removable-field-input').each(function (i, field) {
        $(field).attr('id', fieldname + i).attr('name', fieldname + i)
        $(field).attr('id', fieldname + i).attr('name', fieldname + i)
    });

}

function addField(event) {
    var dyntable = $(this).closest('.DynamicTextFieldList');
    var fieldname = dyntable.data('name');
    var numinputs = dyntable.find('.removable-field-row').length;
    var field = $(
        '<tr class="removable-field-row">\n' +
            '<td><input id="' + fieldname + '-' + numinputs + '" name="' + fieldname + '-' + numinputs + '" type="text" value=""></td>\n' +
            '<td><button type="button" class="removable-field-button">&times;</button></td>\n</tr>'
    );
    console.log(numinputs)
    event.preventDefault();
    $(this).closest('tr').before(field);

}

$(document).ready(function () {
    console.log('start')
    $('.DynamicTextFieldList').on('click', '.removable-field-button', removeField)
        .on('click', '.addable-field-button', addField)
});
var socket = io.connect(location.protocol + '//' + location.host);

function readURL(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
            jQuery($(input).parent()).find("img")
                .attr('src', e.target.result);
        };

        reader.readAsDataURL(input.files[0]);
    }
}

$(function () {
    $(document).on('click', '.btn-add', function (e) {
        e.preventDefault();

        var controlForm = $("#images"),
            currentEntry = $(".image-card:last"),
            newEntry = $(currentEntry.clone()).appendTo(controlForm);

        newEntry.find('input').val('');
        newEntry.find('img').attr("src", "http://placehold.it/120x120");

        controlForm.find('.image-card:not(:last) .btn-add')
            .removeClass('btn-add').addClass('btn-remove')
            .removeClass('btn-success').addClass('btn-danger')
            .html('<i class="fas fa-minus"></i>');
    }).on('click', '.btn-remove', function (e) {
        $(this).parents('.image-card:first').remove();

        e.preventDefault();
        return false;
    });
});

function changeCategories(data) {
    $("select[name='category[]']").html('');
    data.categories.forEach(function (category) {
        $("select[name='category[]']").append("<option value=" + category.id + ">" + category.name + "</option>");
    });
}

$(document).ready(function () {
    $("#addButton").click(function () {
            if ($("#category_name").val()) {
                socket.emit("evAddIAPSCategory", $("#category_name").val());
            }
            $("#categoryModal").modal('hide');
        }
    );
    socket.on('evIAPSCategoriesChanged', changeCategories);
    socket.emit("evAddIAPSCategory");
});
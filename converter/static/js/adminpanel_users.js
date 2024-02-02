$(document).ready(function () {
    $('.save-user-settings-btn').click(function() {
        var userSettings = {};
        $('[name^="is_judge_"], [name^="fio_"], [name^="first_name_"]').each(function() {
            var $input = $(this);
            var splitName = $input.attr('name').split('_');
            var userId = splitName[splitName.length - 1];
            var fieldName = splitName[0];
            userSettings[userId] = userSettings[userId] || {};
            if ($input.is(':checkbox')) {
                userSettings[userId]['judge'] = $input.is(':checked');
            } else {
                userSettings[userId][fieldName] = $input.val();
            }
        });

        sendData('/adminpanel/users', userSettings);
    });

    $('.modal').on('hidden.bs.modal', function() {
        clearModalField($(this));
    });

    $('.add-user-btn').click(function() {
        const newUser = {
            fio: $('#new_user_fio').val(),
            firstName: $('#new_user_first_name').val(),
            password: $('#new_user_password').val(),
            confirmPassword: $('#new_user_confirm_password').val(),
            isJudge: $('#new_user_is_judge').is(':checked')
        };
        sendData('/add-user', newUser);
    });

    $('.save-password-btn').click(function() {
        var modal = $('#changePasswordModal');
        var userId = modal.data('userId');
        var newPassword = $('#new_password').val();
        var confirmPassword = $('#confirm_password').val();
        sendData('/change-password', { userId, newPassword, confirmPassword });
    });

    $('.block-user-btn').click(function() {
        var userId = $(this).data('userId');
        sendData('/block-user', { userId });
    });

    $('[data-utc-time]').each(function() {
        var utcTime = $(this).data('utc-time');
        var date = new Date(utcTime + 'Z');
        var localTime = date.toLocaleString();
        $(this).text(localTime);
    });

    function sendData(url, data) {
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(data) {
                if (data.success) {
                    alert("Успешно: " + data.message);
                    window.location.reload();
                } else {
                    alert("Ошибка: " + data.message);
                }
            },
            error: function(error) {
                alert("Ошибка: " + error.responseText);
            }
        });
    }

    function clearModalField(modal) {
        modal.find('input[type="text"], input[type="password"]').val('');
        modal.find('input[type="checkbox"], input[type="radio"]').prop('checked', false);
    }
    
});
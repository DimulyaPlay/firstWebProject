import { convertUtcToLocalTime, clearModalField } from './modules/utils.js';

$(document).ready(function () {
    $('.save-user-settings-btn').click(function() {
        var userSettings = {};
        $('[name^="judge_"], [name^="reg_"], [name^="fio_"], [name^="login_"]').each(function() {
            var $input = $(this);
            var splitName = $input.attr('name').split('_');
            var userId = splitName[splitName.length - 1];
            var fieldName = splitName[0];
            userSettings[userId] = userSettings[userId] || {};
            if ($input.is(':checkbox')) {
                userSettings[userId][fieldName] = $input.is(':checked');
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
            login: $('#new_user_login').val(),
            password: $('#new_user_password').val(),
            confirmPassword: $('#new_user_confirm_password').val(),
            isJudge: $('#new_user_is_judge').is(':checked'),
            isReg: $('#new_user_is_reg').is(':checked')
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

    $('.block-user-btn').click(function() {
        var userId = $(this).data('userId');
        sendData('/block-user', { userId });
    });

    convertUtcToLocalTime();
    
});
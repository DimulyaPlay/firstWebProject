import { convertUtcToLocalTime } from './modules/utils.js';
convertUtcToLocalTime();
$(document).ready(function () {
    $('tr[data-toggle="modal"]').on('click', function (event) {
        // Проверка, что клик не был сделан на элементе с классом 'no-modal'
        if ($(event.target).hasClass('no-modal')) {
            return;
        }
        const messageId = $(this).data('message-id');
        $.get(`/get_message_data/${messageId}`, function (data) {
            $('body').append(data);
            const modalId = `#myModal${messageId}`;
            convertUtcToLocalTime()
            $(modalId).modal('show');
            $(modalId).on('hidden.bs.modal', function () {
                $(this).remove();
            });

        }).fail(function (error) {
            console.error('Ошибка при получении данных:', error);
        });

    });
});

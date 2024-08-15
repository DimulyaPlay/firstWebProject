import { updatePagination, convertLocalToUtcDate, forwardMessage } from './modules/utils.js';
$(document).ready(function () {

    $('body').on('click', '.page-link', function (e) {
        e.preventDefault();
        var pageNumber = $(this).data('page');
        updateMessagesTable(pageNumber);
    });


    function updateMessagesTable(page) {
        let queryURL = `/api/get-epr-messages?page=${page}`;
        $.ajax({
            url: queryURL,
            type: 'GET',
            dataType: 'json',
            success: function (response) {
                let messages = response.messages;
                let $tbody = $('#messageList');
                let content = '';
                $tbody.empty();
                $tbody.hide();
                if (messages && messages.length > 0) {
                    $.each(messages, function (index, message) {
                        let epr_uploaded = message.epr_uploaded ? 'table-success' : "table-danger";
                        content += `<tr class="${epr_uploaded}" style="text-align: center;" data-message-id="${message.id}">
                                            <td class="align-middle selectable" style="text-align: left;">${message.epr_number}</td>
                                            <td class="align-middle" style="text-align: left;">${message.epr_reason}</td>
                                            <td><a href="/api/get-epr-files?message_id=${message.id}" class="btn btn-primary">Скачать</a></td>
                                            <td>
                                                <form class="upload-form" data-message-id="${message.id}" enctype="multipart/form-data">
                                                    <input type="file" class="d-none file-input" name="uploadedFile" data-message-id="${message.id}">
                                                    <button type="button" class="btn btn-success upload-btn" data-message-id="${message.id}">Загрузить</button>
                                                </form>
                                            </td>
                                        </tr>`;
                    });
    
                } else {
                    $tbody.append('<tr><td colspan="8" class="text-center">Сообщений нет</td></tr>');
                }
                $tbody.append(content);
                $tbody.show();
                updatePagination(response.total_pages, response.current_page, response.start_index_pages, response.end_index_pages);
    
                $('.upload-btn').on('click', function () {
                    let messageId = $(this).data('message-id');
                    $(`.file-input[data-message-id="${messageId}"]`).click();
                });
    
                $('.file-input').on('change', function () {
                    let messageId = $(this).data('message-id');
                    let formData = new FormData($(`.upload-form[data-message-id="${messageId}"]`)[0]);
                    
                    $.ajax({
                        url: `/api/upload-epr-report?msg_id=${messageId}`,
                        type: 'POST',
                        data: formData,
                        processData: false,
                        contentType: false,
                        success: function (response) {
                            if (response.error) {
                                alert(response.error_message);
                            } else {
                                alert('Файл успешно загружен.');
                                updateMessagesTable(1); // обновим таблицу после загрузки
                            }
                        },
                        error: function (xhr, status, error) {
                            console.error("Ошибка загрузки файла: ", error);
                        }
                    });
                });
            },
            error: function (xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }
    updateMessagesTable(1);
});

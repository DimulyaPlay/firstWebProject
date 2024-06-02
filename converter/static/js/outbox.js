import { convertUtcToLocalTime, updatePagination, convertLocalToUtcDate, forwardMessage } from './modules/utils.js';
convertUtcToLocalTime();
$(document).ready(function () {
    $('#messageList').on('click', 'tr[data-toggle="modal"]', function (event) {
        // клик непосредственно по элементу с классом no-modal или по дочернему элементу внутри <a> с классом no-modal
        if ($(event.target).hasClass('no-modal') || $(event.target).closest('a.no-modal').length) {
            return; // Пропускаем событие, если условие выполняется
        }
        const messageId = $(this).data('message-id');
        $.get(`/api/get-message-modal?message_id=${messageId}`, function (data) {
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

    $(document).keypress(function (event) {
        if (event.which === 13) {
            event.preventDefault();
            $('#search').click();
        }
    });

    $('#search').on('click', function (e) {
        let searchString = $('#searchString').val();
        let dateFrom = $('#dateFrom').val();
        let dateTo = $('#dateTo').val();
        // Преобразование дат в UTC
        dateFrom = convertLocalToUtcDate(dateFrom);
        dateTo = convertLocalToUtcDate(dateTo);
        updateMessagesTable(1, searchString, dateFrom, dateTo);
    });

    $('body').on('click', '.page-link', function (e) {
        e.preventDefault();
        let searchString = $('#searchString').val();
        let dateFrom = $('#dateFrom').val();
        let dateTo = $('#dateTo').val();
        // Преобразование дат в UTC
        dateFrom = convertLocalToUtcDate(dateFrom);
        dateTo = convertLocalToUtcDate(dateTo);
        var pageNumber = $(this).data('page');
        updateMessagesTable(pageNumber, searchString, dateFrom, dateTo);
    });

    $(document).on('click', '.cancel-message', function (e) {
        e.preventDefault();
        var messageId = $(this).data('message-id');
        var $tr = $(`tr[data-message-id='${messageId}']`)
        var modalId = `#myModal${messageId}`; // Идентификатор модального окна
        if (confirm("Вы уверены, что хотите отклонить это сообщение? Сообщение и все вложения будут безвозвратно удалены!")) {
            $.ajax({
                url: `/api/cancel-message?message_id=${messageId}`,
                type: 'POST',
                dataType: 'json',
                success: function(response) {
                    if (response.error) {
                        alert("Ошибка: " + response.error_message);
                    } else {
                        alert("Сообщение успешно отклонено.");
                        $(modalId).modal('hide').on('hidden.bs.modal', function () {
                            $(this).remove();
                        });
                        $tr.remove();
                    }
                },
                error: function(xhr, status, error) {
                    alert("Произошла ошибка при попытке отклонить сообщение.");
                }
            });
        }
    });

    $(document).on('keypress', '#emailInput', function(e) {
        if (e.which === 13) {
            e.preventDefault();
            var email = $(this).val().trim();
            if (email) {
                var emailClass = email.replace(/[^a-zA-Z0-9]/g, '');
                var tag = $('<div class="email-tag" name="email">' + email + '<span class="remove-tag">&times;</span></div>');
                $('#emailTags').append(tag);
                var hiddenInput = $('<input type="hidden" name="email" value="' + email + '" class="' + emailClass + '">');
                $('#myModal').append(hiddenInput); // Используйте уникальный селектор модального окна, если у вас их несколько
                $(this).val('');
            }
        }
    });
    
    // Обработчик удаления тега
    $(document).on('click', '.remove-tag', function() {
        $(this).parent().remove();
    });

    // Запуск функции пересылки сообщений из модальных окон
    forwardMessage();

    $(document).on('click', '.archive-message', function (e) {
        e.preventDefault();
        var messageId = $(this).data('message-id');
        var $tr = $(`tr[data-message-id='${messageId}']`)
        if (confirm("Переместить это сообщение в архив?")) {
            $.ajax({
                url: `/api/set-archived?message_id=${messageId}`,
                type: 'GET',
                dataType: 'json',
                success: function(response) {
                    if (response.error) {
                        alert("Ошибка: " + response.error_message);
                    } else {
                        $tr.remove();
                    }
                },
                error: function(xhr, status, error) {
                    alert("Произошла ошибка при попытке архивировать сообщение.");
                }
            });
        }
    });
    

    function updateMessagesTable(page, searchString, dateFrom, dateTo) {
        let queryURL = `/api/outbox-messages?page=${page}&search=${encodeURIComponent(searchString)}`;
        if (dateFrom) {
            queryURL += `&dateFrom=${encodeURIComponent(dateFrom)}`;
        }
        if (dateTo) {
            queryURL += `&dateTo=${encodeURIComponent(dateTo)}`;
        }
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
                        let rowClass = message.signed ? 'table-success' : 'table-warning';
                        let reportIcon = message.responseUUID ? 'report-icon.png' : 'no-report-icon.png';
                        let isResponsed = message.is_responsed ? ' (есть ответы)':'';
                        let filesCount = message.filesCount;
                        content += `<tr class="${rowClass}" style="text-align: center;" data-toggle="modal" data-target="#myModal" data-message-id="${message.id}">
                                            <td class="align-middle" scope="row" style="text-align: left;">${message.mailSubject}${isResponsed}</td>
                                            <td class="align-middle">${filesCount}</td>
                                            <td class="align-middle">${message.sigByName}</td>
                                            <td class="align-middle" data-utc-time="${message.createDatetime}"></td>
                                            <td>
                                            <a href="#" class="no-modal archive-message" data-message-id="${message.id}" style="cursor: pointer;"><img src="static/img/archive-icon.png" alt="Archive"></a>
                                            </td>
                                            <td>
                                                ${message.responseUUID ? `<a href="/api/get-report?message_id=${message.id}" target="_blank" class="no-modal" style="cursor: pointer;"><img src="static/img/${reportIcon}" alt="Report"></a>` : '<img src="static/img/no-report-icon.png" alt="No Report" class="no-modal">'}
                                            </td>
                                        </tr>`;
                    });

                } else {
                    $tbody.append('<tr><td colspan="8" class="text-center">Сообщений нет</td></tr>');
                }
                $tbody.append(content);
                convertUtcToLocalTime();
                $tbody.show()
                updatePagination(response.total_pages, response.current_page, response.start_index_pages, response.end_index_pages);
            },
            error: function (xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }
    updateMessagesTable(1, '');
});

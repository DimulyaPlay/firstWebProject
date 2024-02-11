import { convertUtcToLocalTime, updatePagination } from './modules/utils.js';
convertUtcToLocalTime();
$(document).ready(function () {
    $('#messageList').on('click', 'tr[data-toggle="modal"]', function(event) {
        if ($(event.target).hasClass('no-modal')) {
            return;
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

    $('#search').on('click', function(e) {
        let searchString = $('#searchString').val();
        updateMessagesTable(1, searchString);
    });


    function updateMessagesTable(page, searchString) {
        $.ajax({
            url: `/api/outbox-messages?page=${page}&search=${encodeURIComponent(searchString)}`,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                $('#searchString').val(response.search);
                var messages = response.messages;
                var $tbody = $('#messageList');
                var content = '';
                $tbody.empty();
                $tbody.hide();
                if (messages && messages.length > 0) {
                    $.each(messages, function(index, message) {
                        var rowClass = message.signed ? 'table-success' : 'table-warning';
                        var filesCount = message.filesCount;
                        var toRosreestrIcon = message.toRosreestr ? 'rosreestr-icon.png' : 'no-rosreestr-icon.png';
                        var toEmailsIcon = message.toEmails ? 'email-icon.png' : 'no-email-icon.png';
                        var reportIcon = message.reportDatetime ? 'report-icon.png' : 'no-report-icon.png';
                        content += `<tr class="${rowClass}" style="text-align: center;" data-toggle="modal" data-target="#myModal" data-message-id="${message.id}">
                                            <th class="align-middle" scope="row" style="text-align: left;">${message.mailSubject}</th>
                                            <td class="align-middle">${filesCount}</td>
                                            <td class="align-middle">${message.sigByName}</td>
                                            <td class="align-middle" data-utc-time="${message.createDatetime}"></td>
                                            <td><img src="static/img/${toRosreestrIcon}" alt="Rosreestr"></td>
                                            <td><img src="static/img/${toEmailsIcon}" alt="Email" data-message-id="${message.id}"></td>
                                            <td>
                                                ${message.reportDatetime ? `<a href="/api/get-report?message_id=${message.id}" target="_blank" class="no-modal" style="cursor: pointer;"><img src="static/img/${reportIcon}" alt="Report"></a>` : '<img src="static/img/no-report-icon.png" alt="No Report" class="no-modal">'}
                                            </td>
                                            <td><img src="static/img/email-forward.png" style="text-align: center;" alt="Forward" class="no-modal"></td>
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
            error: function(xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }
    updateMessagesTable(1, '');
});

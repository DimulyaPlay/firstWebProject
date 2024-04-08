export function convertUtcToLocalTime() {
    $('[data-utc-time]').each(function () {
        var utcTime = $(this).data('utc-time');
        // Создаем объект Date, интерпретируя исходную строку времени как UTC
        var date = new Date(utcTime + 'Z'); // Добавляем 'Z' для указания на UTC
        if (!isNaN(date.getTime())) {
            var localTime = date.toLocaleString();
            $(this).text(localTime);
        }
    });
}

export function convertLocalToUtcDate(localDateStr) {
    if (!localDateStr) return ''; // Если дата не задана, возвращаем пустую строку

    var localDate = new Date(localDateStr);
    var timezoneOffset = localDate.getTimezoneOffset() * 60000;
    var utcDate = new Date(localDate.getTime() - timezoneOffset);
    return utcDate.toISOString().slice(0, 10); // Возвращаем только дату в формате YYYY-MM-DD
}

export function clearModalField(modal) {
    modal.find('input[type="text"], input[type="password"]').val('');
    modal.find('input[type="checkbox"], input[type="radio"]').prop('checked', false);
}

export function updatePagination(total_pages, current_page, start_index_pages, end_index_pages) {
    var $pagination = $('.pagination');
    $pagination.empty();
    $pagination.append(`<li class="page-item ${current_page <= 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="1">В начало</a>
    </li>
    <li class="page-item ${current_page == 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${current_page - 1}">Назад</a>
    </li>`);

    for (let page_num = start_index_pages; page_num <= end_index_pages; page_num++) {
        $pagination.append(`<li class="page-item ${page_num == current_page ? 'active' : ''}">
            <a class="page-link" href="#" data-page="${page_num}">${page_num}</a>
        </li>`);
    }

    $pagination.append(`<li class="page-item ${current_page >= total_pages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${current_page + 1}">Вперед</a>
    </li>
    <li class="page-item ${current_page == total_pages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${total_pages}">В конец</a>
    </li>`);
}

export function forwardMessage() {
    $(document).on('click', '.forward-message', function() {
        const modal = $(this).closest('.message-modal');
        const messageId = modal.data('message-id');
        let emails = [];
        modal.find('.tags-container .email-tag').each(function() {
            const email = $(this).text().trim();
            emails.push(email.replace(/×$/, '').trim());
        });
        const emailsStr = emails.join(';');
        $.ajax({
            url: '/api/forward-existing-message',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                message_id: messageId,
                emails: emailsStr
            }),
            success: function(response) {
                alert(response.error_message);
            },
            error: function(error) {
                console.error('Ошибка при пересылке сообщения:', error);
                alert('Произошла ошибка при пересылке сообщения.');
            }
        });
    });
}

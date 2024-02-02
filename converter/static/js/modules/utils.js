export function convertUtcToLocalTime() {
    $('[data-utc-time]').each(function() {
        var utcTime = $(this).data('utc-time');
        // Создаем объект Date, интерпретируя исходную строку времени как UTC
        var date = new Date(utcTime + 'Z'); // Добавляем 'Z' для указания на UTC
        var localTime = date.toLocaleString();
        $(this).text(localTime);
    });
}

export function clearModalField(modal) {
    modal.find('input[type="text"], input[type="password"]').val('');
    modal.find('input[type="checkbox"], input[type="radio"]').prop('checked', false);
}
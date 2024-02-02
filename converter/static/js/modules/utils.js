function convertUtcToLocalTime() {
    $('[data-utc-time]').each(function() {
        var utcTime = $(this).data('utc-time');
        // Создаем объект Date, интерпретируя исходную строку времени как UTC
        var date = new Date(utcTime + 'Z'); // Добавляем 'Z' для указания на UTC
        var localTime = date.toLocaleString();
        $(this).text(localTime);
    });
}



// Экспортируем функцию, чтобы ее можно было использовать в других файлах
module.exports = {
    convertUtcToLocalTime
};
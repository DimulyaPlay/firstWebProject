$(document).ready(function () {
    const MAX_FILE_SIZE = 25 * 1024 * 1024; // Максимальный размер файла (25 МБ)

    // Обработчик для отображения секции email при изменении чекбокса
    $('#sendByEmail').on('change', function () {
        $('#emailSection').toggle(this.checked);
    });

    // Функция для создания нового блока
    function createSignatureFileBlock(index) {
        return `
            <div class="signature-file-block bg-secondary bg-opacity-25 rounded p-1 m-1" data-file-index="${index}">
                <div class="row">
                    <div class="col-md-6 mb-0 mt-2">
                        <label class="form-label">Файл на подпись:
                            <input type="file" class="form-control btn btn-primary"  id="formFile${index}" name="file${index}" accept=".pdf" />
                        </label>
                        <div class="form-check mb-0">
                            <label class="form-check-label">Добавить штамп (только для PDF файлов)
                                <input class="form-check-input addStampCheckbox" type="checkbox" name="addStamp${index}">
                            </label>
                        </div>
                        <div class="stamp-options" style="display: none;">
                            <div class="form-check">
                                <label class="form-check-label">Первая страница
                                    <input class="form-check-input" type="checkbox" name="firstPage${index}">
                                </label>
                            </div>
                            <div class="form-check">
                                <label class="form-check-label">Последняя страница
                                    <input class="form-check-input" type="checkbox" name="lastPage${index}">
                                </label>
                            </div>
                            <div class="form-check">
                                <label class="form-check-label">Все страницы
                                    <input class="form-check-input" type="checkbox" name="allPages${index}">
                                </label>
                            </div>
                            <div class="mb-1">
                                <label class="form-label">Страницы по выбору:
                                    <input type="text" class="form-control" name="customPages${index}"
                                        placeholder="Введите номера страниц">
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-0 mt-2">
                        <label class="form-label">Выберите подпись, если файл подписан:
                            <input type="file" class="form-control btn btn-secondary" name="sig${index}" accept=".sig" />
                        </label>
                        <div class="text-end">
                        <button type="button" class="btn btn-danger btn-sm removeSignatureFileBlock"
                            data-file-index="${index}" style="height: fit-content;">
                            <span aria-hidden="true">&times;</span>
                        </button></div>
                    </div>
                </div>
            </div>
        `;
    }

    // Обработчик клика по кнопке "Добавить еще файл на подпись"
    $('.addSignatureFileBtn').click(function () {
        // Определение текущего индекса
        const index = $('#signatureFilesContainer .signature-file-block').length + 1;
        // Создание и добавление нового блока
        $('#signatureFilesContainer').append(createSignatureFileBlock(index));
    });

    $(document).on('click', '.removeSignatureFileBlock', function () {
        $(this).closest('.signature-file-block').remove();
    });

    // Делегирование события change для динамически добавляемых чекбоксов
    $(document).on('change', '.addStampCheckbox', function () {
        $(this).closest('.signature-file-block').find('.stamp-options').toggle(this.checked);
    });

    $('#signatureFilesContainer').on('change', '[id^="formFile"]', function () {
        const formData = new FormData();
        formData.append('file', $(this)[0].files[0]);
        $.ajax({
            type: 'POST',
            url: '/api/analyze-file',
            data: formData,
            contentType: false,
            processData: false,
            success: function (response) {
                if (response.error) {
                    console.log(response.error_message);
                } else {
                    $('#sendByEmail').prop('checked', true);
                    response.detectedAddresses.forEach(function (address) {
                        var tag = $('<div class="email-tag" name="email">' + address + '<span class="remove-tag">&times;</span></div>');
                        $('#emailTags').append(tag);
                    });
                    $('#emailSection').show()
                }
            },
            error: function (error) {
                console.log('Error:', error);
            }
        });
    });

    // Обработчик для отправки формы
    $('#fileForm').submit(function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        let totalSize = 0;
        for (let pair of formData.entries()) {
            if (pair[1] instanceof File) {
                totalSize += pair[1].size;
            }
        }

        if (totalSize > MAX_FILE_SIZE) {
            alert('Ошибка: Превышен максимально допустимый размер файлов (25 МБ)');
            return;
        }
        // Показываем индикатор загрузки и отключаем кнопку отправки
        $('#loadingSpinner').show();
        $('button[type="submit"]').prop('disabled', true);

        $.ajax({
            type: 'POST',
            url: '/uploadMessage',
            data: formData,
            contentType: false,
            cache: false,
            processData: false,
            success: function (response) {
                if (response.error) {
                    alert(response.error_message);
                    $('#loadingSpinner').hide();
                    $('button[type="submit"]').prop('disabled', false);
                } else {
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                }
            },
            error: function (error) {
                console.log('Ошибка AJAX-запроса:', error);
            }
        });
    });
    $('#emailInput').on('keypress', function (e) {
        if (e.which === 13) { // Код клавиши Enter
            e.preventDefault(); // Предотвращаем отправку формы
            var email = $(this).val().trim();
            if (email) { // Проверяем, не пустой ли email
                var tag = $('<div class="email-tag" name="email">' + email + '<span class="remove-tag">&times;</span></div>');
                $('#emailTags').append(tag);
                $(this).val(''); // Очищаем поле ввода
            }
        }
    });

    $(document).on('click', '.remove-tag', function () {
        $(this).parent().remove();
    });
});

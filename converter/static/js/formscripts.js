$('#sendByEmail').on('change', function() {
    let emailSection = $('#emailSection');
    if (this.checked) {
        emailSection.show();
    } else {
        emailSection.hide();
    }
});

$('#addEmailBtn').on('click', function() {
    let emailInput = $('<input>', {
        type: 'email',
        class: 'form-control',
        style: 'width: 500px;margin-bottom: 10px;',
        name: 'email',
        placeholder: 'Email'
    });
    emailInput.insertBefore($(this));
});

$('#addStamp1').on('change', function() {
    let stampOptions = $('#stampOptions');
    this.checked ? stampOptions.show() : stampOptions.hide();
});

$(document).ready(function () {
    $('.addSignatureFileBtn').on('click', function () {
        let container = $('#signatureFilesContainer');
        let currentIndex = container.children('.signature-file-block').length + 1;

        let newBlock = $('<div>', {
            class: 'signature-file-block',
            'data-file-index': currentIndex
        });

        let label = $('<label>', {
            text: 'Файл на подпись:'
        });

        let fileInput = $('<input>', {
            class: 'btn btn-primary',
            type: 'file',
            name: 'file' + currentIndex,
            id: 'formFile' + currentIndex,
            accept: '.pdf',
            required: true
        });

        label.append('<br>').append(fileInput).append('<br><br>');

        let addStampCheckbox = $('<div>', {
            class: 'form-check'
        }).append($('<label>', {
            class: 'form-check-label'
        }).append($('<input>', {
            class: 'form-check-input addStampCheckbox',
            type: 'checkbox',
            id: 'addStamp' + currentIndex,
            name: 'addStamp' + currentIndex
        })).append('Добавить штамп (только для PDF файлов)'));

        let stampOptions = $('<div>', {
            class: 'stamp-options',
            id: 'stampOptions' + currentIndex,
            style: 'display: none;'
        });

        let firstPageCheckbox = $('<div>', {
            class: 'form-check'
        }).append($('<label>', {
            class: 'form-check-label'
        }).append($('<input>', {
            class: 'form-check-input',
            type: 'checkbox',
            name: 'firstPage' + currentIndex
        })).append('Первая страница'));

        let lastPageCheckbox = $('<div>', {
            class: 'form-check'
        }).append($('<label>', {
            class: 'form-check-label'
        }).append($('<input>', {
            class: 'form-check-input',
            type: 'checkbox',
            name: 'lastPage' + currentIndex
        })).append('Последняя страница'));

        let allPagesCheckbox = $('<div>', {
            class: 'form-check'
        }).append($('<label>', {
            class: 'form-check-label'
        }).append($('<input>', {
            class: 'form-check-input',
            type: 'checkbox',
            name: 'allPages' + currentIndex
        })).append('Все страницы'));

        let customPagesInput = $('<div>', {
            class: 'form-group'
        }).append($('<label>', {
            text: 'Страницы по выбору:'
        })).append($('<input>', {
            type: 'text',
            class: 'form-control',
            name: 'customPages' + currentIndex,
            placeholder: 'Введите номера страниц',
            style: 'width: 300px;'
        }));

        stampOptions.append(firstPageCheckbox)
            .append(lastPageCheckbox)
            .append(allPagesCheckbox)
            .append(customPagesInput);

        newBlock.append(label)
            .append(addStampCheckbox)
            .append(stampOptions);

        container.append('<br>').append(newBlock);
        newBlock.find('.addStampCheckbox').on('change', function () {
            let stampOptions = $(this).closest('.signature-file-block').find('.stamp-options');
            stampOptions.css('display', this.checked ? 'block' : 'none');
        });
    });
});

$(document).ready(function() {
    // Обработчик изменения файла
    $('#signatureFilesContainer').on('change', '[id^="formFile"]', function () {
        // Создаем объект формы и добавляем файл
        let formData = new FormData();
        formData.append('file', $(this)[0].files[0]);

        $.ajax({
            type: 'POST',
            url: '/analyzeFile',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                // Обработка успешного ответа от сервера
                $('#sendByEmail').prop('checked', true);
                data.detectedAddresses.forEach(function(address) {
                    let emailInput = $('<input>', {
                        type: 'email',
                        class: 'form-control',
                        style: 'width: 500px;margin-bottom: 10px;',
                        name: 'email',
                        placeholder: 'Email',
                        value: address
                    });
                    emailInput.insertBefore($('#addEmailBtn'));
                });

                $('#emailSection').show()
            },
            error: function(error) {
                console.log('Error:', error);
            }
        });
    });
});
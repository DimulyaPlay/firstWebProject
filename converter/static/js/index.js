$(document).ready(function () {
    const MAX_FILE_SIZE = 25 * 1024 * 1024; // Максимальный размер файла (25 МБ)

    // Обработчик для отображения секции email при изменении чекбокса
    $('#sendByEmail').on('change', function() {
        $('#emailSection').toggle(this.checked);
    });

    // Обработчик для добавления полей email
    $('#addEmailBtn').on('click', function() {
        const emailInput = $('<input>', {
            type: 'email',
            class: 'form-control mb-2',
            style: 'width: 500px; margin-bottom: 10px;',
            name: 'email',
            placeholder: 'Email'
        });

        const removeButton = $('<button>', {
            class: 'btn btn-danger',
            type: 'button',
            style: 'margin-left: 10px; margin-bottom: 10px;',
            text: 'X',
            click: function () {
                $(this).closest('label').remove();
            }
        });

        const emailLabel = $('<label>', {
            style: 'display: flex;user-select: text;'
        });

        emailLabel.append(emailInput).append(removeButton);
        emailLabel.insertBefore($("#subject"));
    });

    // Обработчик для отображения опций штампа при изменении чекбокса
    $('.addStampCheckbox').on('change', function () {
        const stampOptions = $(this).closest('.signature-file-block').find('.stamp-options');
        stampOptions.toggle(this.checked);
    });

    $('.addSignatureFileBtn').on('click', function () {
        const container = $('#signatureFilesContainer');
        const currentIndex = container.children('.signature-file-block').length + 1;
    
        const newBlock = $('<div>', {
            class: 'signature-file-block',
            'data-file-index': currentIndex
        });
    
        const label = $('<label>', {
            text: 'Файл на подпись:'
        });
    
        const fileInput = $('<input>', {
            class: 'btn btn-primary',
            type: 'file',
            name: 'file' + currentIndex,
            id: 'formFile' + currentIndex,
            accept: '.pdf',
            required: true
        });
    
        const deleteButton = $('<button>', {
            class: 'btn btn-danger deleteSignatureFileBtn',
            text: 'X',
            style: 'margin-left:10px;'
        });
    
        deleteButton.on('click', function () {
            $(this).closest('.signature-file-block').remove();
        });
    
        label.append('<br>').append(fileInput).append(deleteButton).append('<br>');
    
        const labelSig = $('<label>', {
            text: 'Выберите подпись, если файл подписан:'
        });
    
        const fileInputSig = $('<input>', {
            class: 'btn btn-secondary',
            type: 'file',
            name: 'sig' + currentIndex,
            id: 'formFileSignature' + currentIndex,
            accept: '.sig'
        });
    
        labelSig.append('<br>').append(fileInputSig);
    
        const addStampCheckbox = $('<div>', {
            class: 'form-check'
        });
    
        const stampCheckbox = $('<input>', {
            class: 'form-check-input addStampCheckbox',
            type: 'checkbox',
            id: 'addStamp' + currentIndex,
            name: 'addStamp' + currentIndex
        });
    
        addStampCheckbox.append($('<label>', {
            class: 'form-check-label',
            style: 'margin-top: 10px;',
            text: 'Добавить штамп (только для PDF файлов)'
        })).append(stampCheckbox);
    
        const stampOptions = $('<div>', {
            class: 'stamp-options',
            id: 'stampOptions' + currentIndex,
            style: 'display: none;'
        });
    
        const checkboxes = ['Первая страница', 'Последняя страница', 'Все страницы'];
    
        checkboxes.forEach(function (text) {
            const checkbox = $('<input>', {
                class: 'form-check-input',
                type: 'checkbox',
                name: text.toLowerCase() + currentIndex
            });
    
            const label = $('<label>', {
                class: 'form-check-label',
                text: text
            });
    
            const checkboxDiv = $('<div>', {
                class: 'form-check'
            });
    
            checkboxDiv.append(label).append(checkbox);
            stampOptions.append(checkboxDiv);
        });
    
        const customPagesInput = $('<div>', {
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
    
        stampOptions.append(customPagesInput);
    
        newBlock.append('<br>')
            .append(label)
            .append('<br>')
            .append(labelSig)
            .append(addStampCheckbox)
            .append(stampOptions);
    
        container.append(newBlock);
    
        newBlock.find('.addStampCheckbox').on('change', function () {
            const stampOptions = $(this).closest('.signature-file-block').find('.stamp-options');
            stampOptions.toggle(this.checked);
        });
    });
    

    // Обработчик для удаления файлов
    $('#signatureFilesContainer').on('click', '.deleteSignatureFileBtn', function () {
        $(this).closest('.signature-file-block').remove();
    });

    // Обработчик для анализа загружаемого файла
    $('#signatureFilesContainer').on('change', '[id^="formFile"]', function () {
        const formData = new FormData();
        formData.append('file', $(this)[0].files[0]);

        $.ajax({
            type: 'POST',
            url: '/analyzeFile',
            data: formData,
            contentType: false,
            processData: false,
            success: function(data) {
                $('#sendByEmail').prop('checked', true);
                data.detectedAddresses.forEach(function(address) {
                    const emailInput = $('<input>', {
                        type: 'email',
                        class: 'form-control mb-2',
                        style: 'width: 500px; margin-bottom: 10px;',
                        name: 'email',
                        placeholder: 'Email',
                        value: address
                    });

                    const removeButton = $('<button>', {
                        class: 'btn btn-danger',
                        type: 'button',
                        style: 'margin-left: 10px; margin-bottom: 10px;',
                        text: 'X',
                        click: function () {
                            $(this).closest('label').remove();
                        }
                    });

                    const emailLabel = $('<label>', {
                        style: 'display: flex;'
                    });

                    emailLabel.append(emailInput).append(removeButton);
                    emailLabel.insertBefore($("#subject"));
                });

                $('#emailSection').show()
            },
            error: function(error) {
                console.log('Error:', error);
            }
        });
    });

    // Обработчик для отправки формы
    $('#fileForm').submit(function(e) {
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

        $.ajax({
            type: 'POST',
            url: '/uploadMessage',
            data: formData,
            contentType: false,
            cache: false,
            processData: false,
            success: function(response) {
                if (response.error) {
                    alert('Ошибка: ' + response.error_message);
                } else {
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                }
            },
            error: function(error) {
                console.log('Ошибка AJAX-запроса:', error);
            }
        });
    });
});

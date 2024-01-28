$(document).ready(function () {
    $('#sendByEmail').on('change', function() {
        let emailSection = $('#emailSection');
        if (this.checked) {
            emailSection.show();
        } else {
            emailSection.hide();
        }
    });
    
    $('#addEmailBtn').on('click', function() {
        // Создаем новый input
        let emailInput = $('<input>', {
            type: 'email',
            class: 'form-control',
            style: 'width: 500px; margin-bottom: 10px;',
            name: 'email',
            placeholder: 'Email'
        });
    
        // Создаем новую кнопку
        let removeButton = $('<button>', {
            class: 'btn btn-danger',
            id: 'removeEmail',
            type: 'button',
            style: 'margin-left: 10px; margin-bottom: 10px;',
            text: 'X',
            click: function () {
                $(this).closest('label').remove();
            }
        });
    
        // Создаем новый label
        let emailLabel = $('<label>', {
            id: 'emailAdresses',
            style: 'display: flex;user-select: text;'
        });
    
        // Добавляем input и button внутрь label
        emailLabel.append(emailInput);
        emailLabel.append(removeButton);
    
        // Вставляем новый label перед элементом с id "subject"
        emailLabel.insertBefore($("#subject"));
    });
    
    $('#addStamp1').on('change', function() {
        let stampOptions = $('#stampOptions');
        this.checked ? stampOptions.show() : stampOptions.hide();
    });


    $('#saveUserSettings').click(function() {
        var userSettings = {};
        $('[name^="is_judge_"], [name^="fio_"], [name^="first_name_"]').each(function() {
            var $input = $(this);
            var splitName = $input.attr('name').split('_');
            var userId = splitName[splitName.length - 1];
            var fieldName = splitName[0];
    
            if (!userSettings[userId]) {
                userSettings[userId] = {};
            }
    
            if ($input.is(':checkbox')) {
                userSettings[userId]['judge'] = $input.is(':checked');
            } else {
                userSettings[userId][fieldName] = $input.val();
            }
        });
        $.ajax({
            url: '/adminpanel/users',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(userSettings),
            success: function(data) {
                if (data.success) {
                    alert(data.message); // или обработать сообщение другим способом
                    window.location.reload(); // Перезагрузка страницы
                } else {
                    alert(data.message); // или отобразить сообщение об ошибке
                }
            },
            error: function() {
                alert('Произошла ошибка при отправке запроса.');
            }
        });
    });


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


        label.append('<br>').append(fileInput);

        let deleteButton = $('<button>', {
            class: 'btn btn-danger deleteSignatureFileBtn',
            text: 'X',
            style: 'margin-left:10px;',
            click: function () {
                $(this).closest('.signature-file-block').remove();
            }
        });
        label.append(deleteButton);
        label.append('<br>');


        let labelSig = $('<label>', {
            text: 'Выберите подпись, если файл подписан:'
        });

        let fileInputSig = $('<input>', {
            class: 'btn btn-secondary',
            type: 'file',
            name: 'sig' + currentIndex,
            id: 'formFileSignature' + currentIndex,
            accept: '.sig'
        });

        labelSig.append('<br>').append(fileInputSig);


        let addStampCheckbox = $('<div>', {
            class: 'form-check'
        }).append($('<label>', {
            class: 'form-check-label',
            style: 'margin-top: 10px;'
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

        newBlock.append('<br>')
            .append(label)
            .append('<br>')
            .append(labelSig)
            .append(addStampCheckbox)
            .append(stampOptions);



        container.append(newBlock);
        newBlock.find('.addStampCheckbox').on('change', function () {
            let stampOptions = $(this).closest('.signature-file-block').find('.stamp-options');
            stampOptions.css('display', this.checked ? 'block' : 'none');
        });
    });

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
                    // Создаем новый input для найденных в файле адресов
                    let emailInput = $('<input>', {
                        type: 'email',
                        class: 'form-control',
                        style: 'width: 500px; margin-bottom: 10px;',
                        name: 'email',
                        placeholder: 'Email',
                        value: address
                    });
                
                    // Создаем новую кнопку
                    let removeButton = $('<button>', {
                        class: 'btn btn-danger',
                        id: 'removeEmail',
                        type: 'button',
                        style: 'margin-left: 10px; margin-bottom: 10px;',
                        text: 'X',
                        click: function () {
                            $(this).closest('label').remove();
                        }
                    });
                
                    // Создаем новый label
                    let emailLabel = $('<label>', {
                        id: 'emailAdresses',
                        style: 'display: flex;'
                    });
                
                    // Добавляем input и button внутрь label
                    emailLabel.append(emailInput);
                    emailLabel.append(removeButton);
                
                    // Вставляем новый label перед элементом с id "subject"
                    emailLabel.insertBefore($("#subject"));
                });

                $('#emailSection').show()
            },
            error: function(error) {
                console.log('Error:', error);
            }
        });
    });


    $('.change-password-button').click(function() {
        var userId = $(this).data('userId');
        var modal = $('#changePasswordModal');
        modal.data('userId', userId);
    });

    $('.modal').on('hidden.bs.modal', function() {
        $(this).find('input[type="password"]').val('');
    });

    function handleCloseModalAndAlert(modal, message, isSuccess) {
        alert(message);
        if (isSuccess) {
            modal.modal('hide');
        }
    }

    $('.save-password-btn').click(function() {
        var modal = $('#changePasswordModal');
        var userId = modal.data('userId');
        var newPassword = $('#new_password').val();
        var confirmPassword = $('#confirm_password').val();

        $.ajax({
            url: '/change-password',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                userId: userId,
                newPassword: newPassword,
                confirmPassword: confirmPassword
            }),
            success: function(data) {
                handleCloseModalAndAlert(modal, data.message, data.success);
            },
            error: function() {
                alert('Произошла ошибка при отправке запроса.');
            }
        });
    });

    $('[data-bs-toggle="tooltip"]').tooltip();

    $('.btn-sign-file').click(function() {
        const fileId = $(this).data('fileId');
        $.ajax({
            url: '/get_file_for_signing/' + fileId,  // URL для получения файла
            type: 'GET',
            success: function(data) {
                // Перенаправляем файл на локальный сервер для подписи
                fetch('http://localhost:4999/sign_file', {
                    method: 'POST',
                    body: data  // Отправляем файл для подписи
                })
                .then(response => response.blob())
                .then(signature => {
                    // Отправляем подписанный файл обратно на сервер
                    const formData = new FormData();
                    formData.append('fileId', fileId);
                    formData.append('signature', signature);
    
                    fetch('/upload_signature', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(result => {
                        alert(result.message); // Сообщение об успехе или ошибке
                    });
                });
            },
            error: function() {
                alert('Ошибка при получении файла для подписания');
            }
        });
    });

    $('#fileForm').submit(function(e) {
        e.preventDefault();

        // Проверка размера каждого файла перед отправкой
        let totalSize = 0;
        let formData = new FormData(this);

        for (let pair of formData.entries()) {
            if (pair[1] instanceof File) {
                totalSize += pair[1].size;
            }
        }

        if (totalSize > 25 * 1024 * 1024) {
            alert('Ошибка: Превышен максимально допустимый размер файлов (25 МБ)');
            return;
        }

        // Отправка формы через AJAX
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

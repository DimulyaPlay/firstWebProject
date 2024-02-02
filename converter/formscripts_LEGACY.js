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
        let emailInput = $('<input>', {
            type: 'email',
            class: 'form-control',
            style: 'width: 500px; margin-bottom: 10px;',
            name: 'email',
            placeholder: 'Email'
        });
    
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
    
        let emailLabel = $('<label>', {
            id: 'emailAdresses',
            style: 'display: flex;user-select: text;'
        });
    
        emailLabel.append(emailInput);
        emailLabel.append(removeButton);
    
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
                    alert(data.message);
                    window.location.reload();
                } else {
                    alert(data.message);
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
        let formData = new FormData();
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
                    let emailInput = $('<input>', {
                        type: 'email',
                        class: 'form-control',
                        style: 'width: 500px; margin-bottom: 10px;',
                        name: 'email',
                        placeholder: 'Email',
                        value: address
                    });
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
                    let emailLabel = $('<label>', {
                        id: 'emailAdresses',
                        style: 'display: flex;'
                    });
                    emailLabel.append(emailInput);
                    emailLabel.append(removeButton);
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

    $('#addUserModal').on('hidden.bs.modal', function () {
        $(this).find('input[type="text"], input[type="password"]').val('');
        $(this).find('input[type="checkbox"], input[type="radio"]').prop('checked', false);
    });

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

    $('.block-user-btn').click(function() {
        var userId = $(this).data('userId');

        $.ajax({
            url: '/block-user',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                userId: userId,
            }),
            success: function(data) {
                if (data.success) {
                    alert("Успешно: " + data.message);
                    window.location.reload();
                } else {
                    alert("Ошибка: " + data.message);
                }
            }
        });
    });


    $('[data-bs-toggle="tooltip"]').tooltip();
    
    $('.btn-sign-file').click(function() {
        const fileId = $(this).data('fileId');
        const fileName = $(this).data('fileName');
        const selectedCert = $('#certificateSelector').val();
    
        $.ajax({
            url: '/get_file?file_id=' + fileId,
            type: 'GET',
            xhrFields: {
                responseType: 'blob'
            },
            success: function(blob, status, xhr) {
                const fileType = xhr.getResponseHeader('File-Type');
                const sigPages = xhr.getResponseHeader('Sig-Pages');
    
                let formData = new FormData();
                formData.append('file', blob, `document.${fileType}`);
                formData.append('sigPages', sigPages);
                formData.append('fileType', fileType)
                formData.append('selectedCert', selectedCert)
                formData.append('fileName', fileName)
    
                fetch('http://localhost:4999/sign_file', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.blob())
                .then(zipBlob => {
                    uploadSignedFile(fileId, zipBlob);
                })
                .catch(error => {
                    console.error('Ошибка при подписании файла:', error);
                });
            },
            error: function() {
                alert('Ошибка при получении файла для подписания');
            }
        });
    });
    
    function uploadSignedFile(fileId, zipBlob) {
        let formData = new FormData();
        formData.append('fileId', fileId);
        formData.append('file', zipBlob, 'signed_files.zip');
    
        fetch('/upload_signed_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Успешно: " + data.message);
                window.location.reload();
            } else {
                alert("Ошибка: " + data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка при отправке подписанных файлов:', error);
        });
    }

    $('[data-utc-time]').each(function() {
        var utcTime = $(this).data('utc-time');
        // Создаем объект Date, интерпретируя исходную строку времени как UTC
        var date = new Date(utcTime + 'Z'); // Добавляем 'Z' для указания на UTC
        var localTime = date.toLocaleString();
        $(this).text(localTime);
    });

    $('#fileForm').submit(function(e) {
        e.preventDefault();
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

    $('.add-user-btn').click(function() {
        const newUser = {
            fio: $('#new_user_fio').val(),
            firstName: $('#new_user_first_name').val(),
            password: $('#new_user_password').val(),
            confirmPassword: $('#new_user_confirm_password').val(),
            isJudge: $('#new_user_is_judge').is(':checked')
        };
        $.ajax({
            url: '/add-user',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(newUser),
            success: function(data) {
                if (data.success) {
                    alert("Успешно: " + data.message);
                    window.location.reload();
                } else {
                    alert("Ошибка: " + data.message);
                }
            },
            error: function(error) {
                alert("Ошибка: " + error.responseText);
            }
        });
    });
});

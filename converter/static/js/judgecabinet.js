import { convertUtcToLocalTime, updatePagination, forwardMessage } from './modules/utils.js';
$(document).ready(function () {

    $('#fileList').on('click', 'img[data-toggle="modal"]', function () {
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

    $.ajax({
        url: 'http://localhost:4999/get_certs',
        type: 'GET',
        success: function (data) {
            var certificates = data.certificates;
            var lastCert = data.last_cert;
            var $select = $('#certificateSelector');

            certificates.forEach(function (cert) {
                var isSelected = cert === lastCert ? 'selected' : '';
                $select.append(`<option value="${cert}" ${isSelected}>${cert}</option>`);
            });
        },
        error: function () {
            console.log('Не удалось получить список сертификатов. DocumentSIGner запущен?')
            //alert('Не удалось получить список сертификатов. DocumentSIGner запущен?');
        }
    });

    $(document).on('click', '.btn-sign-file', async function () {
        const $button = $(this);
        const fileId = $button.data('fileId');
        const fileName = $button.data('fileName');
        const selectedCert = $('#certificateSelector').val();
        const message_id = $button.data('messageId');
        var $tr = $(`tr[data-file-id='${fileId}']`)
        const $cancelButton = $(`a.cancel-message[data-message-id='${message_id}']`);
        try {
            $button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Подписание...').prop('disabled', true);

            const fileData = await getFileBlob(fileId); // Получаем blob и заголовки
            const zipBlob = await signFile(fileData, fileName, selectedCert); // Передаем все необходимые данные для подписания

            await uploadSignedFile(message_id, fileId, zipBlob);
            $button.html('Подписан').removeClass('btn-primary').addClass('btn-success');
            $tr.removeClass('table-warning').addClass('table-success');
            $cancelButton.prop('disabled', true).addClass('disabled');
        } catch (error) {
            console.error('Ошибка при подписании файла:', error);
            alert('Не удалось подписать документ. DocumentSIGner запущен?');
            $button.html('Подписать').prop('disabled', false).removeClass('btn-success').addClass('btn-primary');
        }
    });

    function getFileBlob(fileId) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: `/api/get-file?file_id=${fileId}`,
                type: 'GET',
                xhrFields: {
                    responseType: 'blob'
                },
                processData: false,
                contentType: false,
                success: function (data, status, xhr) {
                    // Используйте здесь xhr, чтобы получить заголовки
                    const fileType = xhr.getResponseHeader('File-Type');
                    const sigPages = xhr.getResponseHeader('Sig-Pages');
                    resolve({ blob: data, fileType, sigPages });
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    reject(new Error('Ошибка при получении файла: ' + textStatus));
                }
            });
        });
    }

    async function signFile(fileData, fileName, selectedCert) {
        const { blob, fileType, sigPages } = fileData;
        const formData = new FormData();
        formData.append('file', blob);
        formData.append('sigPages', sigPages);
        formData.append('fileType', fileType);
        formData.append('selectedCert', selectedCert);
        formData.append('fileName', fileName);

        const response = await fetch('http://localhost:4999/sign_file', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error('Ошибка при подписании');
        return response.blob();
    }


    async function uploadSignedFile(messageId, fileId, zipBlob) {
        return new Promise((resolve, reject) => {
            var formData = new FormData();
            formData.append('fileId', fileId);
            formData.append('messageId', messageId);
            formData.append('file', zipBlob, 'signed_files.zip');

            $.ajax({
                url: '/api/upload-signed-file',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function (data) {
                    if (data.error) {
                        reject(new Error(data.error_message)); // Отклоняем обещание при ошибке
                    } else {
                        resolve(data); // Разрешаем обещание при успехе
                    }
                },
                error: function (xhr, status, error) {
                    reject(new Error('Ошибка при отправке подписанных файлов: ' + error)); // Отклоняем обещание при ошибке AJAX
                }
            });
        });
    }

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
                success: function (response) {
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
                error: function (xhr, status, error) {
                    alert("Произошла ошибка при попытке отклонить сообщение.");
                }
            });
        }
    });


    $('body').on('click', '.page-link', function (e) {
        e.preventDefault();
        var pageNumber = $(this).data('page');
        updateJudgeTable(pageNumber);
    });

    $('#signedToggle').on('change', function () {
        updateJudgeTable(1); // Обновляем таблицу при каждом переключении
    });

    $('body').on('click', '#fileList tr', function (e) {
        if (!$(e.target).closest('.no-preview').length) {
            let fileId = $(this).data('file-id');
            let fileLink = `/api/get-file?file_id=${fileId}`
            if ($('#pdfPreview').attr('src') == fileLink) {
                togglePreview(false);
                $('#pdfPreview').attr('src', null);
            } else {
                openFileInPreview(fileLink);
                togglePreview(true);
            }
        }
    });

    function openFileInPreview(fileUrl) {
        $('#pdfPreview').attr('src', fileUrl);
    }

    function togglePreview(showPreview) {
        if (showPreview) {
            // Переключаем на режим предпросмотра
            $('#mainContainer').removeClass('container').addClass('container-fluid');
            $('#pdfPreviewContainer').css('flex', '40%');
            $('#tableContainer').css('flex', '60%');
        } else {
            // Возвращаем обратно в исходный режим
            $('#mainContainer').removeClass('container-fluid').addClass('container');
            $('#pdfPreviewContainer').css('flex', '0%');
            $('#tableContainer').css('flex', '100%');
        }
    }

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

    function updateJudgeTable(page) {
        let showAll = $('#signedToggle').is(':checked');
        $.ajax({
            url: `/api/judge-files?page=${page}&showAll=${showAll}`,
            type: 'GET',
            dataType: 'json',
            success: function (response) {
                var files = response.files;
                var content = '';
                var $tbody = $('#fileList');
                $tbody.empty();
                $tbody.hide();
                if (files && files.length > 0) {
                    $.each(files, function (index, file) {
                        var rowClass = file.signed ? 'table-success' : 'table-warning';
                        content += `<tr class="${rowClass}" style="text-align: center;" data-message-id="${file.message_id}" data-file-id="${file.id}">
                                        <th class="align-middle" scope="row" style="text-align: left;">${file.fileDesc}</th>
                                        <td class="align-middle" data-utc-time="${file.createDatetime}"></td>
                                        <td class="align-middle">
                                            <img src="static/img/email-icon.png" class="no-preview" alt="OpenLetter" data-toggle="modal" data-message-id="${file.message_id}" style="cursor: pointer;">
                                        </td>
                                        <td class="align-middle">
                                            <button class="btn btn-primary btn-sign-file no-preview ${file.signed ? '' : 'btn-sm'}" data-file-id="${file.id}" data-message-id="${file.message_id}" data-file-name="${file.fileName}" ${file.signed ? 'disabled>Подписано' : '>Подписать'}</button><br>
                                            ${!file.signed ? `<a href="#" class="btn btn-danger btn-sm mt-1 cancel-message no-preview" data-message-id="${file.message_id}">Отклонить</a>` : ''}
                                        </td>
                                    </tr>`;
                    });
                } else {
                    $tbody.append('<tr><td colspan="5" class="text-center no-preview">Файлы не найдены</td></tr>');
                }
                $tbody.append(content);
                convertUtcToLocalTime();
                $tbody.show();
                updatePagination(response.total_pages, response.current_page, response.start_index_pages, response.end_index_pages);
            },
            error: function (xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }

    updateJudgeTable(1);
    convertUtcToLocalTime();

});

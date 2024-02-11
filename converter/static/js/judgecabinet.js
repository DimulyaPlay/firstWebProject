import { convertUtcToLocalTime, updatePagination } from './modules/utils.js';
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
        try {
            $button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Подписание...').prop('disabled', true);
    
            const fileData = await getFileBlob(fileId); // Получаем blob и заголовки
            const zipBlob = await signFile(fileData, fileName, selectedCert); // Передаем все необходимые данные для подписания
    
            await uploadSignedFile(fileId, zipBlob);
            alert('Файл успешно подписан и загружен.');
            $button.html('Подписан').removeClass('btn-primary').addClass('btn-success');
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
    

    async function uploadSignedFile(fileId, zipBlob) {
        return new Promise((resolve, reject) => {
            var formData = new FormData();
            formData.append('fileId', fileId);
            formData.append('file', zipBlob, 'signed_files.zip');
    
            $.ajax({
                url: '/api/upload-signed-file',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function(data) {
                    if (data.error) {
                        reject(new Error(data.error_message)); // Отклоняем обещание при ошибке
                    } else {
                        resolve(data); // Разрешаем обещание при успехе
                    }
                },
                error: function(xhr, status, error) {
                    reject(new Error('Ошибка при отправке подписанных файлов: ' + error)); // Отклоняем обещание при ошибке AJAX
                }
            });
        });
    }
    


    $('body').on('click', '.page-link', function (e) {
        e.preventDefault(); // Предотвратить переход по ссылке
        var pageNumber = $(this).data('page');
        updateJudgeTable(pageNumber);
    });


    function updateJudgeTable(page) {
        $.ajax({
            url: `/api/judge-files?page=${page}`,
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
                        var rowClass = file.sigNameUUID ? 'table-success' : 'table-warning';
                        content += `<tr class="${rowClass}" style="text-align: center;">
                                        <th class="align-middle" scope="row" style="text-align: left;">${file.fileName}</th>
                                        <td class="align-middle" data-utc-time="${file.createDatetime}"></td>
                                        <td class="align-middle">
                                            <a href="/api/get-file?file_id=${file.id}" target="_blank">
                                                <img src="static/img/file-icon.png" alt="OpenFile">
                                            </a>
                                        </td>
                                        <td class="align-middle">
                                        <img src="static/img/email-icon.png" alt="OpenLetter" data-toggle="modal" data-message-id="${file.message_id}" style="cursor: pointer;">
                                        </td>
                                        <td class="align-middle">
                                            <button class="btn btn-primary btn-sign-file" data-file-id="${file.id}" data-file-name="${file.fileName}" ${file.sigNameUUID ? 'disabled' : ''}>Подписать</button>
                                        </td>
                                       </tr>`;

                    });
                    
                } else {
                    $tbody.append('<tr><td colspan="5" class="text-center">Файлы не найдены</td></tr>');
                }
                $tbody.append(content);
                convertUtcToLocalTime();
                $tbody.show()
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

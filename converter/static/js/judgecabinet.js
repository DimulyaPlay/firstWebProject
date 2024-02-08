import { convertUtcToLocalTime } from './modules/utils.js';
$(document).ready(function () {

    $('tbody').on('click', 'img[data-toggle="modal"]', function () {
        const messageId = $(this).data('message-id');
        $.get(`/get_message_data/${messageId}`, function (data) {
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
        success: function(data) {
            var certificates = data.certificates;
            var lastCert = data.last_cert;
            var $select = $('#certificateSelector');

            certificates.forEach(function(cert) {
                var isSelected = cert === lastCert ? 'selected' : '';
                $select.append(`<option value="${cert}" ${isSelected}>${cert}</option>`);
            });
        },
        error: function() {
            alert('Не удалось получить список сертификатов. DocumentSIGner запущен?');
        }
    });

    $(document).on('click', '.btn-sign-file', function() {
        const $button = $(this);
        const fileId = $(this).data('fileId');
        const fileName = $(this).data('fileName');
        const selectedCert = $('#certificateSelector').val();

        $button.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Подписание...').prop('disabled', true);

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
                    $button.html('Подписан').prop("class", "btn btn-success btn-sign-file");
                })
                .catch(error => {
                    console.error('Ошибка при подписании файла:', error);
                    alert('Не удалось подписать документ. DocumentSIGner запущен?');
                    $button.html('Подписать').prop('disabled', false);
                });
            },
            error: function() {
                alert('Ошибка при получении файла для подписания');
                $button.html('Подписать').prop('disabled', false);
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

    convertUtcToLocalTime();


    $('body').on('click', '.page-link', function(e) {
        e.preventDefault(); // Предотвратить переход по ссылке
        var pageNumber = $(this).data('page');
        updateTable(pageNumber);
    });

    function updateTable(page) {
        $.ajax({
            url: `/api/judge-files?page=${page}`, // Указываем URL вашего API для получения файлов по страницам
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                var files = response.files;
                var $tbody = $('#fileList');
                $tbody.empty();

                if (files && files.length > 0) {
                    $.each(files, function(index, file) {
                        var rowClass = file.sigNameUUID ? 'table-success' : 'table-warning';
                        var fileRow = `<tr class="${rowClass}" style="text-align: center;">
                                        <th class="align-middle" scope="row" style="text-align: left;">${file.fileName}</th>
                                        <td class="align-middle" data-utc-time="${file.createDatetime}"></td>
                                        <td class="align-middle">
                                            <a href="/get_file?file_id=${file.id}" target="_blank">
                                                <img src="static/img/file-icon.png" alt="OpenFile">
                                            </a>
                                        </td>
                                        <td class="align-middle">
                                        <img src="static/img/email-icon.png" alt="OpenLetter" data-toggle="modal" data-message-id="${ file.message_id }" style="cursor: pointer;">
                                        </td>
                                        <td class="align-middle">
                                            <button class="btn btn-primary btn-sign-file" data-file-id="${file.id}" data-file-name="${file.fileName}" ${file.sigNameUUID ? 'disabled' : ''}>Подписать</button>
                                        </td>
                                       </tr>`;
                        $tbody.append(fileRow);
                    });
                    convertUtcToLocalTime();
                } else {
                    $tbody.append('<tr><td colspan="5" class="text-center">Файлы не найдены</td></tr>');
                }
                var total_pages = response.total_pages;
                var current_page = response.current_page;
                var start_index_pages = response.start_index_pages;
                var end_index_pages = response.end_index_pages;
                var $pagination = $('.pagination');
                $pagination.empty();
                $pagination.append(`<li class="page-item ${total_pages <= 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="1">В начало</a>
                </li>
                <li class="page-item ${current_page == 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current_page - 1}">Назад</a>
                </li>`);

                // Генерация кнопок для номеров страниц
                for (let page_num = start_index_pages; page_num <= end_index_pages; page_num++) {
                $pagination.append(`<li class="page-item ${page_num == current_page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${page_num}">${page_num}</a>
                </li>`);
                }

                $pagination.append(`<li class="page-item ${current_page >= total_pages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${current_page + 1}">Вперед</a>
                </li>
                <li class="page-item ${total_pages >= 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${total_pages}">В конец</a>
                </li>`);

            },
            error: function(xhr, status, error) {
                console.error("Ошибка загрузки данных: ", error);
            }
        });
    }

});

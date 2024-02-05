import { convertUtcToLocalTime } from './modules/utils.js';
$(document).ready(function () {
    $('img[data-toggle="modal"]').on('click', function () {
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

    convertUtcToLocalTime();

});

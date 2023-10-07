function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];

    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        const statusDiv = document.getElementById('status');
        statusDiv.innerText = 'Загрузка файла...';

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            statusDiv.innerText = 'Обработка файла...';
            checkProcessingStatus(file.name);  // Передаем имя файла, а не undefined
        })
        .catch(error => console.error('Ошибка загрузки файла:', error));
    } else {
        console.error('Файл не выбран.');
    }
}

function checkProcessingStatus(filename) {
    fetch(`/status/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'complete') {
                const downloadLink = document.createElement('a');
                downloadLink.href = `/get_file/${data.processed_file_path}`;
                downloadLink.download = data.processed_file_path;
                downloadLink.click();
                document.getElementById('status').innerText = 'Файл обработан и готов к скачиванию.';
            } else if (data.status === 'processing') {
                setTimeout(() => checkProcessingStatus(filename), 3000);
            } else {
                document.getElementById('status').innerText = 'Произошла ошибка обработки файла.';
            }
        })
        .catch(error => console.error('Ошибка проверки статуса:', error));
}

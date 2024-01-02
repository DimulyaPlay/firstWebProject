document.getElementById('sendByEmail').addEventListener('change', function() {
    var emailSection = document.getElementById('emailSection');
    if (this.checked) {
        emailSection.style.display = 'block';
    } else {
        emailSection.style.display = 'none';
    }
});

document.getElementById('addEmailBtn').addEventListener('click', function() {
    var emailInput = document.createElement('input');
    emailInput.type = 'email';
    emailInput.className = 'form-control';
    emailInput.style='width: 500px';
    emailInput.name = 'email';
    emailInput.required = true;

    var addEmailBtn = document.getElementById('addEmailBtn');
    addEmailBtn.parentNode.insertBefore(emailInput, addEmailBtn);

    var br = document.createElement('br');
    addEmailBtn.parentNode.insertBefore(br, addEmailBtn);
});

document.getElementById('addStamp1').addEventListener('change', function () {
    var stampOptions = document.getElementById('stampOptions');
    stampOptions.style.display = this.checked ? 'block' : 'none';
});

document.addEventListener('DOMContentLoaded', function () {
    document.querySelector('.addSignatureFileBtn').addEventListener('click', function () {
        let container = document.getElementById('signatureFilesContainer');
        let clonedBlock = container.querySelector('.signature-file-block').cloneNode(true);
        
        // Получение текущего индекса
        let currentIndex = container.children.length;
        
        // Установка новых идентификаторов и имен
        clonedBlock.dataset.fileIndex = currentIndex + 1;
        clonedBlock.querySelector('label').htmlFor = 'formFile' + (currentIndex + 1);
        clonedBlock.querySelector('input[type="file"]').id = 'formFile' + (currentIndex + 1);
        clonedBlock.querySelectorAll('[name]').forEach(function (element) {
            element.name = element.name.replace(/\d+/, currentIndex + 1);
        });
       let br = document.createElement('br');
        container.append(br)
        container.appendChild(clonedBlock);

        // Подключение событий для новых элементов
        clonedBlock.querySelector('.addStampCheckbox').addEventListener('change', function () {
            var stampOptions = this.closest('.signature-file-block').querySelector('.stamp-options');
            stampOptions.style.display = this.checked ? 'block' : 'none';
        });
    });
});
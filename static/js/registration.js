document.addEventListener('DOMContentLoaded', () => {
    const BASE_URL = 'https://188.64.15.189:8443';
    const registrationForm = document.getElementById('registrationForm');
    registrationForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const url = `${BASE_URL}/registerUser`;
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('Регистрация успешна!');
            }
        })
        .catch(error => {
            console.error('Произошла ошибка при регистрации:', error);
            alert('Произошла ошибка при регистрации: ' + error.message);
        });
    });
});
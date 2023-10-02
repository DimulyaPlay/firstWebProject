from flask import Flask, request, jsonify, render_template
import ssl
from flask_sqlalchemy import SQLAlchemy
import os
# Путь к директории с данными приложения
basedir = os.path.abspath(os.path.dirname(__file__))

# Путь к базе данных
database_path = os.path.join(basedir, 'instance', 'users.db')


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database_path
db = SQLAlchemy(app)

# Список для хранения имен
names_list = []


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)


# Методы для работы с пользователями
def add_user(username, password):
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


# Функция для разрешения CORS
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# внесение имени в список
@app.route('/add_name', methods=['POST', 'OPTIONS'])
def add_name():
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'Options Request Received'})
        return add_cors_headers(response)

    name = request.json.get('name')
    names_list.append(name)
    response = jsonify({'message': 'Имя успешно добавлено на сервер'})
    return add_cors_headers(response)


# возврат имен из списка
@app.route('/get_names', methods=['GET'])
def get_names():
    response = jsonify({'names': names_list})
    return add_cors_headers(response)


# Главная страница
@app.route('/', methods=['GET'])
def main_page():
    return render_template('index.html')


# Страница регистрации
@app.route('/registration', methods=['GET'])
def registration():
    return render_template('registration.html')


# Страница входа
@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/registerUser', methods=['POST'])
def registerUser():
    data = request.get_json()  # Получаем данные в формате JSON

    # Проверка наличия обязательных данных в запросе
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Отсутствуют необходимые данные (username и/или password)'}), 400

    # Проверка наличия пользователя с таким именем
    existing_user = get_user_by_username(username)
    if existing_user:
        return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400

    add_user(username, password)
    return jsonify({'message': 'Регистрация успешна!'})


# Авторизация пользователя
@app.route('/loginUser', methods=['POST'])
def loginUser():
    data = request.get_json()  # Получаем данные в формате JSON

    # Проверка наличия обязательных данных в запросе
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Отсутствуют необходимые данные (username и/или password)'}), 400

    user = get_user_by_username(username)
    if user and user.password == password:
        return jsonify({'message': 'Авторизация успешна!'})
    else:
        return jsonify({'error': 'Неверные учетные данные!'}), 400


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        db.session.commit()
    # Загрузка сертификата и ключа
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.load_cert_chain('cert.pem', 'key_unencrypted.pem')
    # app.run(debug=True,  ssl_context=context)

    app.run(debug=True)

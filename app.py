import time

from flask import Flask, request, jsonify, render_template, redirect, send_file
import ssl
from flask_sqlalchemy import SQLAlchemy
import os
import threading
import datetime
from utilities import *
# Путь к директории с данными приложения
basedir = os.path.abspath(os.path.dirname(__file__))

# Путь к базе данных
database_path = os.path.join(basedir, 'instance', 'users.db')


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database_path
db = SQLAlchemy(app)

longtimestorage = os.path.join(basedir, 'uploads', 'longtimestorage')
shorttimestorage = os.path.join(basedir, 'uploads', 'shorttimestorage')

processed_files = {}

job_id = 0
jobs_statuses = {}
temp_file_preset = {
                    'id': "",
                    'filenameStored': "",
                    'filenameUploaded': "",
                    'creatorName': "",
                    'fileWeight': "",
                    'processStatus': "",
                    'uploadedDate': ""
                    }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)


class ProcessedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filenameStored = db.Column(db.String(120), unique=True, nullable=False)
    filenameUploaded = db.Column(db.String(120), unique=False, nullable=False)
    creatorName = db.Column(db.String(120), unique=False, nullable=False)
    fileWeight = db.Column(db.Integer, unique=False, nullable=False)
    processStatus = db.Column(db.Boolean, unique=False, nullable=False)
    uploadedDate = db.Column(db.Date, default=datetime.datetime.utcnow)


# Методы для работы с пользователями
def add_user(username, password):
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()


# Функция для разрешения CORS
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


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

# Страница загрузки
@app.route('/uploader', methods=['GET'])
def uploader():
    return render_template('uploader.html')



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


@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filepath = os.path.join(shorttimestorage, file.filename)
    file.save(filepath)
    # Запускаем поток для обработки файла
    processing_thread = threading.Thread(target=process_and_notify, args=(filepath,file.filename))
    processing_thread.start()

    return jsonify({'message': 'File uploaded and is being processed.'})


def process_and_notify(file_path, filename):
    processed_file_path, message = process_file(file_path)
    # Сохраняем информацию об обработанном файле
    processed_files[filename] = {
        'processed_file_path': processed_file_path,
        'message': message,
        'created': time.time()
    }


@app.route('/status/<filename>')
def check_processing_status(filename):
    if filename in processed_files:
        return jsonify({
            'status': 'complete',
            'processed_file_path': filename,
            'message': processed_files[filename]['message']
        })
    else:
        return jsonify({'status': 'processing'})


@app.route('/get_file/<filename>')
def get_file(filename):
    return send_file(processed_files[filename]['processed_file_path'], as_attachment=True)


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

    print('cleaning temp files after restart')
    for filename in os.listdir(shorttimestorage):
        try:
            os.remove(os.path.join(shorttimestorage, filename))
        except:
            traceback.print_exc()
    print('starting garbage cleaner')
    cleaner_thread = threading.Thread(target=file_cleaner, args=(processed_files,))
    cleaner_thread.start()
    print('garbage cleaner started')
    # Загрузка сертификата и ключа
    # context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    # context.load_cert_chain('cert.pem', 'key_unencrypted.pem')
    # app.run(debug=True,  ssl_context=context)
    app.run(debug=True)

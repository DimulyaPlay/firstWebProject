import random
import time
import traceback
from .auth import login
from flask import Flask, request, render_template, url_for, redirect, send_file, jsonify, Blueprint, flash
from flask_login import current_user, login_user, logout_user
from .models import Users, UploadedFiles, Judges, UploadedMessages
from werkzeug.security import check_password_hash
import os
from . import db
views = Blueprint('views', __name__)


# Главная страница
@views.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        login()
    if current_user.is_authenticated:
        judges = Judges.query.all()
        return render_template('index.html', title='Главная страница', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Главная страница', user=current_user)


@views.route('/get_report/<fileId>')
def get_file(filename):
    return send_file(processed_files[filename]['processed_file_path'], as_attachment=False)


@views.route('/get_judge_filelist/<judge_id>')
def get_judge_filelist(judge_id):
    judge = Judges.query.filter_by(judge_id=judge_id)
    if judge:
        files = UploadedFiles.query.filter_by(judge_id=judge_id)
        files_data = {}
        if files:
            for f in files:
                files_data[f.id] = f.id
                files_data[f.id] = f.filePath
                files_data[f.id] = f.fileName
                files_data[f.id] = f.sigPages
            return jsonify(files_data)
        else:
            return 0
    else:
        return 0


@views.post('/uploadMessage')
def upload_file():
    # Получение данных из формы
    form_data = request.form.lists()
    files_data = request.files.lists()
    for key, value in files_data:
        print(key, value)
    for key, value in form_data:
        print(key, value)
    judgeFio = request.form.get('judge')
    toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
    toEmails = True if request.form.get('sendByEmail') == 'on' else False

    if toEmails:
        # Если отправка по эл. почте включена, получите адреса эл. почты
        emails = ';'.join(request.form.getlist('email'))
        toEmails = emails if emails else ''
    else:
        toEmails = ''

    # Получение всех файлов из формы
    files = request.files.getlist('file')

    # Обработка каждого файла
    for file in files:
    # Ваш код для обработки каждого файла
        ...

    # Пример сохранения первого файла
    if files:
        file = files[0]
        judge = Judges.query.filter_by(fio=judgeFio).first()
        filepath = os.path.join(judge.inputStorage, file.filename)

        # Ваш код для обработки файла
        # ...

        # Пример добавления информации о файле в базу данных
        user_id = int(current_user.id)
        mailSubject = 'TEMP'
        new_row = ProcessedFile(
            filePath=filepath,
            fileName=os.path.basename(filepath),
            user_id=user_id,
            toRosreestr=toRosreestr,
            toEmails=toEmails,
            judge_id=judge.id,
            mailSubject=mailSubject
        )
        db.session.add(new_row)
        current_user.last_judge = judge.id

    db.session.commit()
    flash('Файл(ы) отправлен(ы)', category='success')
    return redirect('/')


import random
import time
import traceback
from .auth import login
from flask import Flask, request, render_template, url_for, redirect, send_file, jsonify, Blueprint, flash
from flask_login import current_user, login_user, logout_user
from .models import User, ProcessedFile, Judge
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
        judges = Judge.query.all()
        return render_template('index.html', title='Главная страница', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Главная страница', user=current_user)


@views.route('/get_report/<fileId>')
def get_file(filename):

    return send_file(processed_files[filename]['processed_file_path'], as_attachment=False)


@views.post('/upload')
def upload_file():
    file = request.files['file']
    data = request.form
    judgeFio = data.get('judge')
    toRosreestr = True if data.get('sendToRosreestr') == 'on' else False
    toEmails = True if data.get('sendByEmail') == 'on' else False
    if toEmails:
        emails = ';'.join(data.getlist('email'))
        if emails:
            toEmails = emails
        else:
            toEmails = ''
    else:
        toEmails = ''
    judge = Judge.query.filter_by(fio=judgeFio).first()
    filepath = os.path.join(judge.inputStorage, file.filename)
    filepath_db = ProcessedFile.query.filter_by(filenameStored=filepath).first()
    while os.path.exists(filepath) or filepath == filepath_db.filenameStored:
        filepath = os.path.join(judge.inputStorage, file.filename[:-4] + str(random.randint(0, 999)) + '.pdf')
    file.save(filepath)
    user_id = int(current_user.id)
    new_row = ProcessedFile(filenameStored=filepath, filenameUploaded=os.path.basename(filepath), user_id=user_id, toRosreestr=toRosreestr, toEmails=toEmails)
    db.session.add(new_row)
    db.session.commit()
    flash('Файл отправлен', category='success')
    return redirect('/')


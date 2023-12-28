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
        last_judge = current_user.last_judge if current_user.last_judge in [judge.fio for judge in judges] else None
        return render_template('index.html', title='Главная страница', user=current_user, judges=judges, last_judge=last_judge)
    else:
        return render_template('login.html', title='Главная страница', user=current_user)


@views.route('/get_report/<fileId>')
def get_file(filename):
    return send_file(processed_files[filename]['processed_file_path'], as_attachment=False)


@views.route('/get_judge_filelist/<fio>')
def get_judge_filelist(fio):
    judge = Judge.query.filter_by(fio = fio)
    if judge:
        files = ProcessedFile.query.filter_by(judge_fio=fio)
        files_data = {}
        if files:
            for f in files:
                files_data[f.id] = f.filePath
                files_data[f.id] = f.fileName
                files_data[f.id] = f.sigPages
            return jsonify(files_data)
        else:
            return {}
    else:
        return 0


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
    while os.path.exists(filepath) or (filepath_db and filepath == filepath_db.filenameStored):
        filepath = os.path.join(judge.inputStorage, file.filename[:-4] + str(random.randint(0, 999)) + '.pdf')
    file.save(filepath)
    user_id = int(current_user.id)
    mailSubject = 'TEMP'
    new_row = ProcessedFile(filePath=filepath,
                            fileName=os.path.basename(filepath),
                            user_id=user_id,
                            toRosreestr=toRosreestr,
                            toEmails=toEmails,
                            judge_fio=judgeFio,
                            mailSubject=mailSubject)
    db.session.add(new_row)
    current_user.last_judge = judgeFio
    db.session.commit()
    flash('Файл отправлен', category='success')
    return redirect('/')


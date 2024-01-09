import random
import sys
import time
import datetime
import traceback
from .auth import login
from flask import Flask, request, render_template, url_for, redirect, send_file, jsonify, Blueprint, flash
from flask_login import current_user, login_user, logout_user, login_required
from .models import Users, UploadedFiles, Judges, UploadedMessages
from werkzeug.security import check_password_hash
import os
from . import db
from .Utils import analyze_file, generate_sig_pages, check_sig, config, export_signed_message, report_exists
from uuid import uuid4
import base64

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


@views.route('/outbox', methods=['GET'])
@login_required
def outbox():
    return render_template('outbox.html', title='Мои отправления', user=current_user, report_exists=report_exists)


@views.route('/get_report/<messageId>')
@login_required
def get_report(messageId):
    report_filepath = os.path.join(config['reports_path'], f'{messageId}.pdf')
    if os.path.exists(report_filepath):
        return send_file(report_filepath, as_attachment=False)
    else:
        flash('Файл отчета не обнаружен', category='error')


@views.route('/get_judge_filelist')
@login_required
def get_judge_filelist():
    judge_id = current_user.judge_id
    files = UploadedFiles.query.filter_by(judge_id=judge_id, sigPath=None).all()
    files_data = {}
    if files:
        for f in files:
            files_data[f.id] = {'id': f.id,
                                'fileName': f.fileName,
                                'sigPages': f.sigPages
                                }
        return jsonify(files_data)
    else:
        return jsonify({})


@views.route('/download_file/<file_id>')
@login_required
def download_file(file_id):
    file = UploadedFiles.query.get(file_id)
    if file and file.filePath:
        return send_file(file.filePath, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'})


@views.route('/set_file_signed/<file_id>', methods=['POST'])
@login_required
def set_file_signed(file_id):
    try:
        file = UploadedFiles.query.filter_by(id=file_id).first()
        file_path = file.filePath
        sig_path = file.filePath+'.sig'
        file.sigPath = file.filePath+'.sig'
        file.sigName = file.fileName + '.sig'
        # Принимаем файлы от клиента
        pdf_file = request.files.get('pdf_file')
        sig_file = request.files.get('sig_file')

        if pdf_file:
            pdf_file.save(file_path)

        if sig_file:
            sig_file.save(sig_path)

        if os.path.isfile(sig_path):
            if config['sig_check']:
                if not check_sig(file_path, sig_path):
                    return jsonify(0), 400
            db.session.commit()
            message_files = UploadedFiles.query.filter_by(message_id=file.message_id).all()
            all_files_signed = all(file.sigName for file in message_files)
            if all_files_signed:
                message = UploadedMessages.query.filter_by(id=file.message_id).first()
                message.signed = True
                export_signed_message(message)
                db.session.commit()
            return jsonify(1), 200
        else:
            return jsonify(0), 400
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return jsonify(0), 400


@views.post('/uploadMessage')
@login_required
def upload_file():
    try:
        files_data = request.files.lists()
        attachments = request.files.getlist('attachments')
        form_data = request.form.lists()
        judgeFio = request.form.get('judge')
        judge = Judges.query.filter_by(fio=judgeFio).first()
        toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
        toEmails = True if request.form.get('sendByEmail') == 'on' else False
        if toEmails:
            emails = '; '.join(request.form.getlist('email'))
            toEmails = emails if emails else None
        else:
            toEmails = None
        new_message = UploadedMessages(toRosreestr=toRosreestr,
                                       sigBy=judge.fio,
                                       toEmails=toEmails,
                                       mailSubject=request.form.get('subject'),
                                       mailBody=request.form.get('body'),
                                       user_id=current_user.id)
        db.session.add(new_message)
        db.session.commit()
        message_id = new_message.id
        for key, value in files_data:
            if key.startswith('file'):
                idx = key[4:]
                filepath = os.path.join(config['file_storage'], str(uuid4()) + '.pdf')
                value[0].save(filepath)
                addStamp = True if request.form.get('addStamp'+idx) == 'on' else False
                allPages = True if request.form.get('allPages' + idx, default=False) == 'on' else False
                if allPages:
                    sig_page_str = 'all'
                if addStamp and not allPages:
                    sig_page_list = []
                    lastPage = True if request.form.get('lastPage' + idx, default=False) == 'on' else False
                    firstPage = True if request.form.get('firstPage' + idx, default=False) == 'on' else False
                    customPages = request.form.get('customPages' + idx, default=False)
                    if firstPage:
                        sig_page_list.append(1)
                    if lastPage:
                        sig_page_list.append(-1)
                    sig_page_str = generate_sig_pages(sig_page_list, customPages)
                if not allPages and not addStamp:
                    sig_page_str = ''
                newFile = UploadedFiles(
                    filePath=filepath,
                    fileName=value[0].filename,
                    sigPages=sig_page_str,
                    user_id=current_user.id,
                    judge_id=judge.id,
                    message_id=message_id,
                    sigBy=judgeFio)
                db.session.add(newFile)
        for attachment in attachments:
            if attachment.filename:
                file_extention = "." + attachment.filename.rsplit('.', 1)[-1]
                filepath = os.path.join(config['file_storage'], str(uuid4()) + file_extention)
                attachment.save(filepath)
                newFile = UploadedFiles(
                    filePath=filepath,
                    fileName=attachment.filename,
                    user_id=current_user.id,
                    message_id=message_id)
                db.session.add(newFile)
        current_user.last_judge = judge.id
        db.session.commit()
        flash('Файл(ы) отправлен(ы)', category='success')
        return redirect('/')
    except:
        db.session.rollback()
        traceback.print_exc()
        flash('Ошибка создания сообщения', category='error')
        return redirect('/')
    finally:
        db.session.close()


@views.route('/analyzeFile', methods=['POST'])
@login_required
def analyzeFile():
    file = request.files['file']
    detected_addresses = analyze_file(file)
    if detected_addresses:
        return jsonify(detectedAddresses=detected_addresses)
    else:
        return jsonify(error='No addresses detected in the file'), 400


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
from .Utils import analyze_file, generate_sig_pages, check_sig, config, export_signed_message, report_exists, save_file
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
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search_query = request.args.get('search', '')
    filtered_messages = [message for message in current_user.messages if search_query.lower() in message.mailSubject.lower()]
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_messages = filtered_messages[start_index:end_index]
    total_pages = (len(filtered_messages) + per_page - 1) // per_page
    start_index_pages = page-3 if page-3 > 1 else 1
    end_index_pages = page+3 if page+3 < total_pages else total_pages
    return render_template('outbox.html', title='Мои отправления',
                           user=current_user,
                           messages=paginated_messages,
                           report_exists=report_exists,
                           search_query=search_query,
                           total_pages=total_pages,
                           current_page=page,
                           start_index_pages=start_index_pages,
                           end_index_pages=end_index_pages)


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
        new_files_data = {}
        for key, value in files_data:
            if key != 'attachments' and value[0].filename:
                new_files_data[key] = value[0]
        attachments = request.files.getlist('attachments')
        attachments = [attachment for attachment in attachments if attachment.filename]
        judgeFio = request.form.get('judge')
        judge = Judges.query.filter_by(fio=judgeFio).first()
        toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
        toEmails = True if request.form.get('sendByEmail') == 'on' else None
        if toEmails:
            emails = '; '.join(request.form.getlist('email'))
            toEmails = emails if emails else None
        else:
            toEmails = None
        subject = request.form.get('subject', None)
        if toEmails and not subject:
            error_message = 'Тема сообщения отсутствует, отправка отменена'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        body = request.form.get('body')
        if not (toEmails or toRosreestr):
            error_message = 'Не выбрана ни один адрес отправки, отправка отменена'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        try:
            new_message = UploadedMessages(toRosreestr=toRosreestr,
                                           sigBy=judge.fio,
                                           toEmails=toEmails,
                                           mailSubject=subject,
                                           mailBody=body,
                                           user_id=current_user.id)
            db.session.add(new_message)
            db.session.commit()
        except Exception as e:
            traceback.print_exc()
            error_message = f'Ошибка при создани письма, отправка отменена ({e})'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        message_id = new_message.id
        if new_files_data:
            for key, value in new_files_data.items():
                if key.startswith('file'):
                    idx = key[4:]
                    filepath = save_file(value)
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
                    sigfile = [value for key, value in new_files_data.items() if key == 'sig'+str(idx)][0]
                    if sigfile:
                        sigPath = filepath+'.sig'
                        sigName = sigfile.filename
                        sigfile.save(sigPath)
                        sig_valid = check_sig(filepath, sigPath)
                        if not sig_valid:
                            db.session.rollback()
                            return jsonify({'error': True, 'error_message': f'Прикрепленная к файлу {value.filename} подпись не прошла проверку, отправка отменена'})
                    else:
                        sigPath = None
                        sigName = None
                    try:
                        newFile = UploadedFiles(
                            filePath=filepath,
                            fileName=value.filename,
                            sigPages=sig_page_str,
                            sigPath=sigPath,
                            sigName=sigName,
                            user_id=current_user.id,
                            judge_id=judge.id,
                            message_id=message_id,
                            sigBy=judgeFio)
                        db.session.add(newFile)
                    except Exception as e:
                        traceback.print_exc()
                        error_message = f'Ошибка при сохранении файла {value.filename}, отправка отменена ({e})'
                        db.session.rollback()
                        return jsonify({'error': True, 'error_message': error_message})
        if attachments:
            for attachment in attachments:
                try:
                    filepath = save_file(attachment)
                    newFile = UploadedFiles(
                        filePath=filepath,
                        fileName=attachment.filename,
                        sigName='No_need',
                        user_id=current_user.id,
                        message_id=message_id)
                    db.session.add(newFile)
                except Exception as e:
                    traceback.print_exc()
                    error_message = f'Ошибка при сохранении файла {attachment.filename}, отправка отменена ({e})'
                    db.session.rollback()
                    return jsonify({'error': True, 'error_message': error_message})
        current_user.last_judge = judge.id
        db.session.commit()
        try:
            message_files = UploadedFiles.query.filter_by(message_id=message_id).all()
            all_files_signed = all(file.sigName for file in message_files)
            if all_files_signed:
                new_message = UploadedMessages.query.filter_by(id=message_id).first()
                new_message.signed = True
                export_signed_message(new_message)
                db.session.commit()
                flash('Сообщение успешно выведено к отправке.', category='success')
                return jsonify({'success': True, 'redirect_url': url_for('views.home')})
        except Exception as e:
            traceback.print_exc()
            error_message = f'Ошибка при отправке подписанного письма ({e}).'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        flash('Файл(ы) отправлен(ы) на подпись.', category='success')
        return jsonify({'success': True, 'redirect_url': url_for('views.home')})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        error_message = f'Ошибка {e}'
        return jsonify({'error': True, 'error_message': error_message})
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


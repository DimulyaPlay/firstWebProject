import time
import traceback
from .auth import login
from flask import request, render_template, url_for, send_file, jsonify, Blueprint, flash, redirect, make_response, render_template_string
from flask_login import current_user, login_required, logout_user
from .models import UploadedFiles, UploadedMessages, Users
from sqlalchemy import desc
import os
from datetime import datetime, timedelta
from . import db, free_mails_limit
from uuid import uuid4
from .Utils import analyze_file, generate_sig_pages, check_sig, config, export_signed_message, report_exists, \
    save_config, read_create_config, process_emails, generate_modal, hwid, sent_mails_in_current_session, is_valid
from email_validator import validate_email
import zipfile
import tempfile

views = Blueprint('views', __name__)


@views.before_request
def before_request():
    if current_user.is_authenticated:
        if int(config['auth_timeout']) and (current_user.last_seen < datetime.utcnow() - timedelta(hours=int(config['auth_timeout']))):  # 2 часа неактивности
            logout_user()
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@views.route('/', methods=['GET'])
def home_redirector():
    if current_user.is_authenticated:
        if current_user.is_judge:
            return redirect(url_for('views.judge_cabinet'))
        judges = Users.query.filter_by(is_judge=True)
        return render_template('index.html', title='Отправить письмо', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Войти', user=current_user)


@views.route('/create_message', methods=['GET'])
def create_message():
    if current_user.is_authenticated:
        if not is_valid and len(sent_mails_in_current_session) > free_mails_limit:
            flash('Лимит сообщений исчерпан, новые сообщения отправляться не будут.', 'error')
        judges = Users.query.filter_by(is_judge=True)
        return render_template('index.html', title='Отправить письмо', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Войти', user=current_user)


@views.route('/judge', methods=['GET'])
@login_required
def judge_cabinet():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filtered_files = (UploadedFiles.query
                      .filter(UploadedFiles.sigById == current_user.id)
                      .order_by(desc(UploadedFiles.createDatetime)).all())
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_files = filtered_files[start_index:end_index]
    total_pages = (len(filtered_files) + per_page - 1) // per_page
    start_index_pages = page - 3 if page - 3 > 1 else 1
    end_index_pages = page + 3 if page + 3 < total_pages else total_pages
    return render_template('judgecabinet.html', title='Кабинет судьи', user=current_user,
                           files=paginated_files,
                           total_pages=total_pages,
                           current_page=page,
                           start_index_pages=start_index_pages,
                           end_index_pages=end_index_pages)


@views.route('/api/judge-files', methods=['GET'])
@login_required
def get_judge_files():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filtered_files = (UploadedFiles.query
                      .filter(UploadedFiles.sigById == current_user.id)
                      .order_by(desc(UploadedFiles.createDatetime)).all())
    total_files = len(filtered_files)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_files = filtered_files[start_index:end_index]

    files_data = []
    for file in paginated_files:
        files_data.append({
            'fileName': file.fileName,
            'createDatetime': file.createDatetime.isoformat(),
            'id': file.id,
            'sigNameUUID': bool(file.sigNameUUID),
            'message_id': file.message_id
        })
    total_pages = (total_files + per_page - 1) // per_page
    start_index_pages = page - 3 if page - 3 > 1 else 1
    end_index_pages = page + 3 if page + 3 < total_pages else total_pages
    return jsonify({
        'files': files_data,
        'total_pages': total_pages,
        'current_page': page,
        "start_index_pages": start_index_pages,
        "end_index_pages": end_index_pages
    })


@views.route('/admin', methods=['GET'])
@login_required
def adminpanel():
    return render_template('adminpanel.html', title='Панель управления', user=current_user)


@views.route('/adminpanel/system', methods=['GET', 'POST'])
@login_required
def adminpanel_system():
    global config
    if request.method == 'GET':
        return render_template('adminpanel_system.html',
                               title='Панель управления',
                               user=current_user,
                               default_configuration=config,
                               hwid=hwid)
    if request.method == 'POST':
        try:
            sig_check = request.form.get('sig_check') == 'on'  # Преобразование в boolean
            csp_path = request.form.get('csp_path')
            file_storage = request.form.get('file_storage')
            file_export_folder = request.form.get('file_export_folder')
            reports_path = request.form.get('reports_path')
            if sig_check:
                if not os.path.exists(csp_path):
                    flash('Параметры не были сохранены, недействительный путь к Крипто Про', category='error')
                    return redirect(url_for('views.adminpanel_system'))
            if not all((os.path.exists(file_storage), os.path.exists(file_export_folder), os.path.exists(reports_path))):
                flash('Параметры не были сохранены, один или несколько из путей для хранения недоступны', category='error')
                return redirect(url_for('views.adminpanel_system'))
            l_key = request.form.get('l_key')
            config['sig_check'] = sig_check
            config['csp_path'] = csp_path
            config['file_storage'] = file_storage
            config['file_export_folder'] = file_export_folder
            config['reports_path'] = reports_path
            config['auth_timeout'] = request.form.get('auth_timeout')
            config['l_key'] = l_key
            config['restricted_emails'] = request.form.get('restricted_emails')
            save_config()
            flash('Параметры успешно сохранены', category='success')
        except:
            config = read_create_config()
            traceback.print_exc()
            flash('Параметры не были сохранены', category='error')
        return redirect(url_for('views.adminpanel_system'))


@views.route('/adminpanel/users', methods=['GET', 'POST'])
@login_required
def adminpanel_users():
    global config
    if request.method == 'GET':
        users_table = Users.query.filter_by().all()
        return render_template('adminpanel_users.html',
                               title='Панель управления',
                               user=current_user,
                               default_configuration=config,
                               users_table=users_table)
    if request.method == 'POST':
        try:
            data = request.json
            for user_id, user_data in data.items():
                user = Users.query.get(user_id)
                if user:
                    user.is_judge = user_data.get('judge', user.is_judge)
                    user.fio = user_data.get('fio', user.fio)
                    user.first_name = user_data.get('first_name', user.first_name)
                    db.session.commit()
            return jsonify({'success': True, 'message': 'Параметры успешно сохранены'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Параметры не были сохранены: ' + str(e)})


@views.route('/outbox', methods=['GET'])
@login_required
def outbox():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search_query = request.args.get('search', '')
    if current_user.first_name != 'admin':
        filtered_messages = (UploadedMessages.query
                             .filter(UploadedMessages.user == current_user,
                                     UploadedMessages.mailSubject.ilike(f"%{search_query}%"))
                             .order_by(desc(UploadedMessages.createDatetime))  # Сортировка по убыванию времени создания
                             .all())
    else:
        filtered_messages = (UploadedMessages.query
                             .filter(UploadedMessages.mailSubject.ilike(f"%{search_query}%"))
                             .order_by(desc(UploadedMessages.createDatetime))  # Сортировка по убыванию времени создания
                             .all())
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_messages = filtered_messages[start_index:end_index]
    total_pages = (len(filtered_messages) + per_page - 1) // per_page
    start_index_pages = page-3 if page-3 > 1 else 1
    end_index_pages = page+3 if page+3 < total_pages else total_pages
    return render_template('outbox.html',
                           title='Мои отправления',
                           user=current_user,
                           messages=paginated_messages,
                           report_exists=report_exists,
                           search_query=search_query,
                           total_pages=total_pages,
                           current_page=page,
                           start_index_pages=start_index_pages,
                           end_index_pages=end_index_pages)


@views.route('/get_report', methods=['GET'])
@login_required
def get_report():
    idx = request.args.get('message_id', 1, type=int)
    msg = UploadedMessages.query.get(idx)
    report_filepath = os.path.join(config['file_storage'], msg.reportNameUUID)
    if os.path.exists(report_filepath):
        return send_file(report_filepath, as_attachment=False)
    else:
        return jsonify({'error': 'File not found'})


@views.route('/get_message_data/<msg_id>', methods=['GET'])
@login_required
def get_message_data(msg_id):
    msg = UploadedMessages.query.get(msg_id)
    if msg:
        modal = generate_modal(msg)
        return render_template_string(modal)
    else:
        return jsonify({'error': 'File not found'})


@views.route('/get_file', methods=['GET'])
@login_required
def get_file():
    idx = request.args.get('file_id', 1, type=int)
    file_obj = UploadedFiles.query.get(idx)
    if not file_obj:
        return jsonify({'error': 'File not found in DB'})
    file_path = os.path.join(config['file_storage'], file_obj.fileNameUUID)
    if os.path.exists(file_path):
        response = make_response(send_file(file_path, as_attachment=False, download_name=file_obj.fileName))
        response.headers['Sig-Pages'] = file_obj.sigPages
        response.headers['File-Type'] = file_obj.fileType
        return response
    else:
        return jsonify({'error': 'File not found in storage'})


@views.post('/uploadMessage')
@login_required
def upload_file():
    global sent_mails_in_current_session
    try:
        if not is_valid and len(sent_mails_in_current_session) > free_mails_limit:
            error_message = 'Лимит сообщений исчерпан.'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        files_data = request.files.lists()
        new_files_data = {}
        for key, value in files_data:
            if key != 'attachments' and value[0].filename:
                new_files_data[key] = value[0]
        attachments = request.files.getlist('attachments')
        attachments = [attachment for attachment in attachments if attachment.filename]
        judgeFio = request.form.get('judge')
        judge = Users.query.filter_by(fio=judgeFio).first()
        toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
        toEmails = process_emails(request.form)
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
        if not new_files_data and toRosreestr:
            error_message = 'в Росреестр недопустима отправка сообщения без вложений'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        try:
            new_message = UploadedMessages(toRosreestr=toRosreestr,
                                           sigById=judge.id,
                                           sigByName=judgeFio,
                                           toEmails=toEmails,
                                           mailSubject=subject,
                                           mailBody=body,
                                           user_id=current_user.id)
            db.session.add(new_message)
            db.session.commit()
        except Exception as e:
            traceback.print_exc()
            error_message = f'при создани письма, отправка отменена ({e})'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        message_id = new_message.id
        if new_files_data:
            for key, value in new_files_data.items():
                if key.startswith('file'):
                    idx = key[4:]
                    file_type = os.path.splitext(value.filename)[1][1:]
                    file_name_uuid = str(uuid4()) + '.' + file_type
                    file_name = value.filename
                    filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
                    value.save(filepath_to_save)
                    addStamp = True if request.form.get('addStamp'+idx) == 'on' else False
                    allPages = True if request.form.get('allPages' + idx, default=False) == 'on' else False
                    sig_page_str = ''
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
                    if allPages:
                        sig_page_str = 'all'
                    if not addStamp:
                        sig_page_str = ''
                    sigfile = [value for key, value in new_files_data.items() if key == 'sig'+str(idx)]
                    if sigfile:
                        sigNameUUID = file_name_uuid+'.sig'
                        sig_path_to_save = os.path.join(config['file_storage'], sigNameUUID)
                        sigName = sigfile[0].filename
                        sigfile[0].save(sig_path_to_save)
                        if config['sig_check']:
                            sig_valid = check_sig(filepath_to_save, sig_path_to_save)
                            if not sig_valid:
                                db.session.rollback()
                                return jsonify({'error': True, 'error_message': f'Прикрепленная к файлу {value.filename} подпись не прошла проверку, отправка отменена'})
                    else:
                        sigNameUUID = None
                        sigName = None
                    try:
                        newFile = UploadedFiles(
                            fileNameUUID=file_name_uuid,
                            fileName=file_name,
                            sigPages=sig_page_str,
                            sigNameUUID=sigNameUUID,
                            fileType=file_type,
                            sigName=sigName,
                            user_id=current_user.id,
                            message_id=message_id,
                            sigById=judge.id,
                            sigByName=judgeFio)
                        db.session.add(newFile)
                    except Exception as e:
                        traceback.print_exc()
                        error_message = f'при сохранении файла {value.filename}, отправка отменена ({e})'
                        db.session.rollback()
                        return jsonify({'error': True, 'error_message': error_message})
        if attachments:
            for attachment in attachments:
                try:
                    file_name = attachment.filename
                    file_type = os.path.splitext(file_name)[1][1:]
                    file_name_uuid = str(uuid4()) + '.' + file_type
                    filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
                    attachment.save(filepath_to_save)
                    newFile = UploadedFiles(
                        fileNameUUID=file_name_uuid,
                        fileName=file_name,
                        fileType=file_type,
                        sigName='No_need',
                        user_id=current_user.id,
                        message_id=message_id)
                    db.session.add(newFile)
                except Exception as e:
                    traceback.print_exc()
                    error_message = f'при сохранении файла {attachment.filename}, отправка отменена ({e})'
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
                sent_mails_in_current_session += "1"
                flash('Сообщение успешно отправлено.', category='success')
                return jsonify({'success': True, 'redirect_url': url_for('views.create_message')})
        except Exception as e:
            traceback.print_exc()
            error_message = f'при экспорте готового письма ({e}).'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        sent_mails_in_current_session += "1"
        flash('Сообщение передано на подпись. После подписания будет отправлено.', category='success')
        return jsonify({'success': True, 'redirect_url': url_for('views.create_message')})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        error_message = f'Ошибка {e}'
        return jsonify({'error': True, 'error_message': error_message})
    finally:
        db.session.close()


@views.route('/upload_signed_file', methods=['POST'])
@login_required
def upload_signed_file():
    try:
        file_id = request.form['fileId']
        zip_file = request.files['file']
        file = UploadedFiles.query.get(file_id)
        file_path = os.path.join(config['file_storage'], file.fileNameUUID)
        file.sigNameUUID = file.fileNameUUID + '.sig'
        file.sigName = file.fileName + '.sig'
        sig_path = os.path.join(config['file_storage'], file.sigNameUUID)
        fd, temp_zip = tempfile.mkstemp(f'.zip')
        os.close(fd)
        zip_file.save(temp_zip)
        zip_path = temp_zip
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files_in_zip = zipf.namelist()
            for file_in_zip in files_in_zip:
                if file_in_zip.endswith('.sig'):
                    zipf.extract(file_in_zip, os.path.dirname(sig_path))
                    os.replace(os.path.join(os.path.dirname(sig_path), file_in_zip), sig_path)
                else:
                    zipf.extract(file_in_zip, os.path.dirname(file_path))
                    os.replace(os.path.join(os.path.dirname(file_path), file_in_zip), file_path)
        os.remove(zip_path)
        if config['sig_check']:
            if not check_sig(file_path, sig_path):
                return jsonify({'success':False, 'message':'Подпись не прошла проверку на сервере'})
        db.session.commit()
        message_files = UploadedFiles.query.filter_by(message_id=file.message_id).all()
        all_files_signed = all(file.sigName for file in message_files)
        if all_files_signed:
            message = UploadedMessages.query.filter_by(id=file.message_id).first()
            message.signed = True
            export_signed_message(message)
            db.session.commit()
        return jsonify({'success': True, 'message': 'Документ подписан успешно'})
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'message': e})


@views.route('/analyzeFile', methods=['POST'])
@login_required
def analyzeFile():
    file = request.files['file']
    detected_addresses = analyze_file(file)
    if detected_addresses:
        return jsonify(detectedAddresses=detected_addresses)
    else:
        return jsonify(error='No addresses detected in the file'), 400


import traceback
from .auth import login
from flask import request, render_template, url_for, send_file, jsonify, Blueprint, flash, redirect
from flask_login import current_user, login_required
from .models import UploadedFiles, UploadedMessages, Users
from sqlalchemy import desc
import os
from . import db
from .Utils import analyze_file, generate_sig_pages, check_sig, config, export_signed_message, report_exists, save_file, save_config, read_create_config
from email_validator import validate_email

views = Blueprint('views', __name__)


# Главная страница
@views.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        login()
    if current_user.is_authenticated:
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
                         .filter(UploadedFiles.sigBy == current_user.fio)
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


@views.route('/admin', methods=['GET'])
@login_required
def adminpanel():
    return render_template('adminpanel.html', user=current_user)


@views.route('/adminpanel/system', methods=['GET', 'POST'])
@login_required
def adminpanel_system():
    global config
    if request.method == 'GET':
        return render_template('adminpanel_system.html',
                               user=current_user,
                               default_configuration=config)
    if request.method == 'POST':
        try:
            sig_check = request.form.get('sig_check') == 'on'  # Преобразование в boolean
            csp_path = request.form.get('csp_path', '')
            file_storage = request.form.get('file_storage', '')
            file_export_folder = request.form.get('file_export_folder', '')
            reports_path = request.form.get('reports_path', '')
            config['sig_check'] = sig_check
            config['csp_path'] = csp_path
            config['file_storage'] = file_storage
            config['file_export_folder'] = file_export_folder
            config['reports_path'] = reports_path
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
    filtered_messages = (UploadedMessages.query
                         .filter(UploadedMessages.user == current_user,
                                 UploadedMessages.mailSubject.ilike(f"%{search_query}%"))
                         .order_by(desc(UploadedMessages.createDatetime))  # Сортировка по убыванию времени создания
                         .all())
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


@views.route('/get_report', methods=['GET'])
@login_required
def get_report():
    idx = request.args.get('message_id', 1, type=int)
    report_filepath = os.path.join(config['reports_path'], f'{idx}.pdf')
    if os.path.exists(report_filepath):
        return send_file(report_filepath, as_attachment=False)
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
        judge = Users.query.filter_by(fio=judgeFio).first()
        toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
        toEmails = True if request.form.get('sendByEmail') == 'on' else None
        if toEmails:
            emails = '; '.join([email for email in request.form.getlist('email') if validate_email(email)])
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
        if not new_files_data and toRosreestr:
            error_message = 'в Росреестр недопустима отправка сообщения без вложений'
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
            error_message = f'при создани письма, отправка отменена ({e})'
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
                            message_id=message_id,
                            sigBy=judge.id)
                        db.session.add(newFile)
                    except Exception as e:
                        traceback.print_exc()
                        error_message = f'при сохранении файла {value.filename}, отправка отменена ({e})'
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
                flash('Сообщение успешно отправлено.', category='success')
                return jsonify({'success': True, 'redirect_url': url_for('views.home')})
        except Exception as e:
            traceback.print_exc()
            error_message = f'при экспорте готового письма ({e}).'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        flash('Сообщение передано на подпись. После подписания будет отправлено.', category='success')
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
def analyze_file():
    file = request.files['file']
    detected_addresses = analyze_file(file)
    if detected_addresses:
        return jsonify(detectedAddresses=detected_addresses)
    else:
        return jsonify(error='No addresses detected in the file'), 400


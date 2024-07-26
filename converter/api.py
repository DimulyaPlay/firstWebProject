import time
import traceback
from .auth import login
from flask import request, jsonify, Blueprint, after_this_request, make_response, send_file, render_template_string, flash, url_for
from flask_login import current_user, login_required
from .models import UploadedFiles, UploadedMessages, Users, Notifications, UploadedSigs, ExternalSenders, UploadedAttachments
from sqlalchemy import desc, case, and_
from .Utils import analyze_file, config, generate_modal_message, delayed_file_removal, export_files_to_epr, process_epr, process_description, convert_to_pdf, are_all_files_signed, generate_new_thread_id, sent_mails_in_current_session, process_files, check_sig, export_signed_message, is_valid, process_emails, generate_sig_pages, process_emails2
import os
from . import db, free_mails_limit, convert_types_list
import tempfile
import zipfile
import shutil
from uuid import uuid4
from datetime import datetime, timedelta
from threading import Thread


api = Blueprint('api', __name__)


@api.get('/judge-files')
@login_required
def get_judge_files():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    show_all = request.args.get('showAll', 'false').lower() == 'true'
    # Получаем сообщения, подписанные текущим пользователем
    base_query = UploadedMessages.query.filter(UploadedMessages.sigById == current_user.id)
    # Если не показывать все, то фильтруем неподписанные файлы
    if not show_all:
        base_query = base_query.filter(
            ~UploadedMessages.files.any(UploadedFiles.signed == True)
        )
    # Пагинация сообщений
    pagination = base_query.order_by(
        case((~UploadedMessages.files.any(UploadedFiles.signed == True), 0), else_=1),
        desc(UploadedMessages.createDatetime)
    ).paginate(page=page, per_page=per_page, error_out=False)
    paginated_messages = pagination.items
    total_pages = pagination.pages if pagination.pages else 1
    # Извлекаем файлы из сообщений
    files_data = []
    for message in paginated_messages:
        for file in message.files:
            if file.sig_required:
                files_data.append({
                    'fileName': file.fileName,
                    'fileDesc': f'{message.description} ({file.fileName})',
                    'createDatetime': file.createDatetime.isoformat(),
                    'id': file.id,
                    'signed': bool(file.signed),
                    'message_id': message.id
                })
    # Сортируем файлы по дате создания
    files_data.sort(key=lambda x: x['createDatetime'], reverse=True)
    return jsonify({
        'files': files_data,
        'total_pages': total_pages,
        'current_page': page,
        "start_index_pages": max(1, page - 3),
        "end_index_pages": min(page + 3, total_pages)
    })


@api.get('/outbox-messages')
@login_required
def get_out_messages():
    page = request.args.get('page', 1, type=int)
    archived = request.args.get('archive', 'false').lower() == 'true'
    per_page = 10
    search_query = request.args.get('search', '')
    date_from = request.args.get('dateFrom', None)
    date_to = request.args.get('dateTo', None)
    base_query = UploadedMessages.query.filter(
        and_(
            UploadedMessages.mailSubject.ilike(f"%{search_query}%"),
            UploadedMessages.is_incoming == False
        )
    )
    # Фильтрация по архивным сообщениям
    if archived:
        base_query = base_query.filter(UploadedMessages.archived == True)
    else:
        base_query = base_query.filter(UploadedMessages.archived == False)
    # Фильтрация сообщений по пользователю (если не админ)
    if current_user.login != 'admin':
        base_query = base_query.filter(UploadedMessages.user == current_user)
    # Фильтрация по дате
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        base_query = base_query.filter(UploadedMessages.createDatetime >= date_from)
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        # Добавляем один день к date_to и вычитаем 1 секунду, чтобы получить конец дня
        date_to = date_to + timedelta(days=1) - timedelta(seconds=1)
        base_query = base_query.filter(UploadedMessages.createDatetime <= date_to)
    # Добавляем условную сортировку: неподписанные сообщения будут в начале списка
    messages_query = base_query.order_by(
        case((UploadedMessages.signed == False, 0), else_=1),
        desc(UploadedMessages.createDatetime)
    )
    pagination = messages_query.paginate(page=page, per_page=per_page, error_out=False)
    total_pages = pagination.pages if pagination.pages else 1
    paginated_messages = pagination.items
    messages_data = [{
        'mailSubject': message.description,
        'createDatetime': message.createDatetime.isoformat(),
        'signed': message.signed,
        'id': message.id,
        'sigByName': message.sigByName,
        'filesCount': len(message.files),
        'is_responsed': message.is_responsed,
        'is_declined': message.is_declined,
        'responseUUID': bool(message.responseUUID)
    } for message in paginated_messages]
    return jsonify({
        'messages': messages_data,
        'total_pages': total_pages,
        'current_page': page,
        "start_index_pages": max(1, page - 3),
        "end_index_pages": min(page + 3, total_pages),
    })


@api.get('/get-epr-messages')
@login_required
def get_epr_messages():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    empty_toEpr_messages = UploadedMessages.query.filter(
        UploadedMessages.toEpr.isnot(None),
        UploadedMessages.signed.is_(True)
    ).order_by(
        desc(UploadedMessages.createDatetime)
    )
    status_mapping = {
        '0': 'Ответ',
        '1': 'Возвращено для устр. недост.',
        '2': 'Возвращено без рассмотрения'
    }
    pagination = empty_toEpr_messages.paginate(page=page, per_page=per_page, error_out=False)
    total_pages = pagination.pages if pagination.pages else 1
    paginated_messages = pagination.items
    messages_data = [{
        'id': message.id,
        'epr_number': message.toEpr.split(':')[0],
        'epr_reason': status_mapping[message.toEpr.split(':')[1]],
        'epr_uploaded': bool(message.epr_uploadedUUID)
    } for message in paginated_messages]
    return jsonify({
        'messages': messages_data,
        'total_pages': total_pages,
        'current_page': page,
        "start_index_pages": max(1, page - 3),
        "end_index_pages": min(page + 3, total_pages),
    })


@api.route('/get-epr-files', methods=['GET'])
def get_epr_files():
    idx = request.args.get('message_id', 1, type=int)
    message_obj = UploadedMessages.query.get(idx)
    tempdir = tempfile.mkdtemp()
    try:
        zip_for_export = export_files_to_epr(message_obj, tempdir)
        @after_this_request
        def cleanup(response):
            try:
                Thread(target=delayed_file_removal, args=([tempdir],)).start()
            except Exception as e:
                print(f'Error starting cleanup thread: {e}')
            return response

        return send_file(zip_for_export, as_attachment=True, download_name=os.path.basename(zip_for_export))
    except Exception as e:
        shutil.rmtree(tempdir)
        raise e


@api.get('/get-epr-messages_pm')
def get_epr_messages_pm():
    empty_toEpr_messages = UploadedMessages.query.filter(
        UploadedMessages.toEpr.isnot(None),
        UploadedMessages.signed.is_(True),
        UploadedMessages.epr_uploadedUUID.isnot('')
    ).order_by(
        desc(UploadedMessages.createDatetime)
    )
    status_mapping = {
        '0': 'Ответ',
        '1': 'Возвращено для устр. недост.',
        '2': 'Возвращено без рассмотрения'
    }
    messages_data = [{
        'id': message.id,
        'epr_number': message.toEpr.split(':')[0],
        'epr_reason': status_mapping[message.toEpr.split(':')[1]]
    } for message in empty_toEpr_messages]
    return jsonify({
        'messages': messages_data
    })


@api.route('/analyze-file', methods=['POST'])
@login_required
def analyzefile():
    try:
        file = request.files['file']
        detected_addresses = analyze_file(file)
        if detected_addresses:
            return jsonify(detectedAddresses=detected_addresses)
        else:
            error_message = 'adresov ne naydeno'
            return jsonify({'error': True, 'error_message': error_message})
    except Exception as e:
        error_message = f'ошибка при анализе файла:  {e}'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-notifications', methods=['GET'])
@login_required
def get_notifications():
    if current_user:
        user_notifications = [note.message for note in current_user.notifications]
        # Удалить уведомления после их отправки пользователю
        Notifications.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify(user_notifications), 200
    else:
        return jsonify([], 400)


@api.route('/get-file', methods=['GET'])
@login_required
def get_file():
    idx = request.args.get('file_id', 1, type=int)
    file_obj = UploadedFiles.query.get(idx)
    if not file_obj:
        error_message = 'Ошибка: файл не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    file_path = os.path.join(config['file_storage'], file_obj.fileNameUUID)
    if os.path.exists(file_path):
        response = make_response(send_file(file_path, as_attachment=False, download_name=file_obj.fileName))
        response.headers['Sig-Pages'] = file_obj.sigPages
        response.headers['File-Type'] = file_obj.fileType
        return response
    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-gf', methods=['GET'])
@login_required
def get_gf():
    idx = request.args.get('file_id', 1, type=int)
    file_obj = UploadedFiles.query.get(idx)
    if not file_obj:
        error_message = 'Ошибка: файл не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    file_path = os.path.join(config['file_storage'], file_obj.gf_fileNameUUID)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False, download_name=file_obj.gf_fileNameUUID)

    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})

@api.route('/get-epr-report', methods=['GET'])
@login_required
def get_epr_report():
    idx = request.args.get('message_id', 1, type=int)
    file_obj = UploadedMessages.query.get(idx)
    file_path = os.path.join(config['file_storage'], file_obj.epr_uploadedUUID)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-sign', methods=['GET'])
@login_required
def get_sign():
    idx = request.args.get('file_id', 1, type=int)
    file_obj = UploadedFiles.query.get(idx)
    if not file_obj or not file_obj.signatures:
        error_message = 'Ошибка: файл подписи не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    sign_path = os.path.join(config['file_storage'], file_obj.signatures[0].sigNameUUID)
    if os.path.exists(sign_path):
        # Отправка файла подписи
        return send_file(sign_path, as_attachment=True, download_name=file_obj.signatures[0].sigName)
    else:
        error_message = 'Ошибка: файл подписи не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get_attachment/<file_uuid>', methods=['GET'])
def get_attachment(file_uuid):
    file_obj = UploadedAttachments.query.filter_by(fileNameUUID=file_uuid).first()
    if not file_obj:
        error_message = 'Ошибка: файл не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    file_path = os.path.join(config['msg_attachments_dir'], file_obj.fileNameUUID)
    file_name = f'{file_obj.fileNameUUID}.{file_obj.fileType}'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False, download_name=file_name)
    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-report', methods=['GET'])
@login_required
def get_report():
    idx = request.args.get('message_id', 1, type=int)
    msg_obj = UploadedMessages.query.get(idx)
    if not msg_obj or not msg_obj.responseUUID:
        error_message = 'Ошибка: письмо или отчет не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    report_path = os.path.join(config['file_storage'], msg_obj.responseUUID)
    if os.path.exists(report_path):
        # Отправка файла подписи
        return send_file(report_path, as_attachment=False, download_name=msg_obj.responseUUID)
    else:
        error_message = 'Ошибка: файл подписи не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-message-modal', methods=['GET'])
@login_required
def get_message_modal():
    msg_id = request.args.get('message_id', 1, type=int)
    msg = UploadedMessages.query.get(msg_id)
    modal = generate_modal_message(msg)
    return render_template_string(modal)


@api.route('/upload-signed-file', methods=['POST'])
@login_required
def upload_signed_file():
    try:
        print(request.form)
        file_id = request.form['fileId']
        message_id = request.form['messageId']
        zip_file = request.files['file']
        file = UploadedFiles.query.get(file_id)
        message = UploadedMessages.query.get(message_id)
        if not file:
            return jsonify({'error': True, 'error_message': 'Файл не найден'})
        file_path = os.path.join(config['file_storage'], file.fileNameUUID)
        sig_name_uuid = file.fileNameUUID + '.sig'
        sig_path = os.path.join(config['file_storage'], sig_name_uuid)
        gf_file_path = os.path.join(config['file_storage'], f'gf_{file.fileNameUUID}')
        fd, zip_path = tempfile.mkstemp('.zip')
        os.close(fd)
        zip_file.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files_in_zip = zipf.namelist()
            for file_in_zip in files_in_zip:
                if file_in_zip.endswith('.sig'):
                    zipf.extract(file_in_zip, os.path.dirname(sig_path))
                    os.replace(os.path.join(config['file_storage'], file_in_zip), sig_path)
                elif file_in_zip.startswith('gf_') and file.sigPages:
                    zipf.extract(file_in_zip, os.path.dirname(gf_file_path))
                    os.replace(os.path.join(config['file_storage'], file_in_zip), gf_file_path)
                else:
                    zipf.extract(file_in_zip, os.path.dirname(file_path))
                    os.replace(os.path.join(config['file_storage'], file_in_zip), file_path)
        os.remove(zip_path)
        if config['sig_check']:
            if not check_sig(file_path, sig_path):
                error_message = 'Ошибка: Подпись не прошла проверку.'
                return jsonify({'error': True, 'error_message': error_message})
        new_sig = UploadedSigs(
            sigNameUUID=sig_name_uuid,
            sigName=file.fileName+'.sig')
        message.sigs.append(new_sig)
        file.signature = new_sig
        file.signed = True
        if file.sigPages:
            file.gf_fileNameUUID = f'gf_{file.fileNameUUID}'
        db.session.commit()
        all_files_signed = are_all_files_signed(message)
        if all_files_signed:
            message.signed = True
            export_signed_message(message)
            db.session.commit()
        return jsonify({'error': False, 'error_message': 'Файл успешно подписан.'})
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        error_message = f'Ошибка: {e}'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/upload-epr-report', methods=['POST'])
@login_required
def upload_epr_report(filepath=None):
    try:
        if os.path.isfile(filepath):
            try:
                filename = os.path.basename(filepath)
                msg_id = filename.split('-')[1]
                msg = UploadedMessages.query.get(msg_id)
                file_type = os.path.splitext(filename)[1][1:]
                file_name_uuid = str(uuid4()) + '.' + file_type
                filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
                shutil.move(filepath, filepath_to_save)
                msg.epr_uploadedUUID = file_name_uuid
                db.session.commit()
                return 1
            except:
                traceback.print_exc()
                return 0

        uploaded_file = request.files.get('uploadedFile')
        file_type = os.path.splitext(uploaded_file.filename)[1][1:]
        file_name_uuid = str(uuid4()) + '.' + file_type
        filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
        uploaded_file.save(filepath_to_save)
        msg.epr_uploadedUUID = file_name_uuid
        db.session.commit()
        return jsonify({'error': False, 'error_message': 'Файл успешно загружен.'})
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        error_message = f'Ошибка: {e}'
        return jsonify({'error': True, 'error_message': error_message})


@api.post('/create-new-message')
@login_required
def create_new_message():
    global sent_mails_in_current_session
    try:
        if not is_valid and len(sent_mails_in_current_session) > free_mails_limit:
            return jsonify({'error': True, 'error_message': 'Лимит сообщений исчерпан.'})
        new_files_data, attachments = process_files(request.files)
        sig_required = False
        judgeFio = request.form.get('judge')
        judge = Users.query.filter_by(fio=judgeFio).first()
        toRosreestr = True if request.form.get('sendToRosreestr') == 'on' else False
        toEpr = process_epr(request.form)
        toEmails = process_emails(request.form)
        subject = request.form.get('subject')
        description = process_description(request.form)
        if toEmails and not subject:
            error_message = 'Тема сообщения отсутствует, отправка отменена'
            return jsonify({'error': True, 'error_message': error_message})
        body = request.form.get('body')
        if not (toEmails or toRosreestr or toEpr):
            error_message = 'Не выбрана ни один адрес отправки, отправка отменена'
            return jsonify({'error': True, 'error_message': error_message})
        if not new_files_data and toRosreestr:
            error_message = 'в Росреестр недопустима отправка сообщения без вложений'
            return jsonify({'error': True, 'error_message': error_message})
        try:
            new_message = UploadedMessages(description=description,
                                           toRosreestr=toRosreestr,
                                           toEmails=toEmails,
                                           toEpr=toEpr,
                                           mailSubject=subject,
                                           mailBody=body,
                                           thread_id=generate_new_thread_id()
                                           )
            current_user.messages.append(new_message)
        except Exception as e:
            traceback.print_exc()
            error_message = f'при создани письма, отправка отменена ({e})'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        if new_files_data:
            sig_required = True
            for key, value in new_files_data.items():
                if key.startswith('file'):
                    idx = key[4:]
                    file_type = os.path.splitext(value.filename)[1][1:]
                    file_name_uuid = str(uuid4()) + '.' + file_type
                    file_name = value.filename
                    filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
                    value.save(filepath_to_save)
                    sigfile = [value for key, value in new_files_data.items() if key == 'sig' + str(idx)]
                    if not sigfile and file_type in convert_types_list:
                        file_type = 'pdf'
                        file_name_uuid_old = file_name_uuid
                        file_name_uuid = str(uuid4()) + '.' + file_type
                        file_name = value.filename + '_converted.pdf'
                        new_filepath_to_save = os.path.join(config['file_storage'], file_name_uuid)
                        try:
                            convert_to_pdf(filepath_to_save, new_filepath_to_save)
                        except:
                            traceback.print_exc()
                            file_type = os.path.splitext(value.filename)[1][1:]
                            file_name_uuid = file_name_uuid_old
                            file_name = value.filename
                    addStamp = True if request.form.get('addStamp'+idx) == 'on' else False
                    allPages = True if request.form.get('allPages'+idx) == 'on' else False
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
                    try:
                        newFile = UploadedFiles(
                            fileNameUUID=file_name_uuid,
                            fileName=file_name,
                            fileType=file_type,
                            sig_required=True,
                            sigPages=sig_page_str)
                        newSig = None
                        if sigfile:
                            sigNameUUID = file_name_uuid + '.sig'
                            sig_path_to_save = os.path.join(config['file_storage'], sigNameUUID)
                            sigName = sigfile[0].filename
                            sigfile[0].save(sig_path_to_save)
                            if config['sig_check']:
                                sig_valid = check_sig(filepath_to_save, sig_path_to_save)
                                if not sig_valid:
                                    db.session.rollback()
                                    return jsonify({'error': True,
                                                    'error_message': f'Прикрепленная к файлу {value.filename} подпись не прошла проверку, отправка отменена'})
                            newSig = UploadedSigs(
                                sigNameUUID=sigNameUUID,
                                sigName=sigName)
                        if newSig:
                            new_message.sigs.append(newSig)
                            newFile.signature = newSig
                            newFile.signed = True
                        else:
                            message = f"Пользователь {current_user.fio} направил документы на подпись."
                            new_note = Notifications(user_id=judge.id,
                                                     message=message)
                            db.session.add(new_note)
                        current_user.files.append(newFile)
                        new_message.files.append(newFile)
                        db.session.commit()
                    except Exception as e:
                        traceback.print_exc()
                        error_message = f'при сохранении файла {value.filename}, отправка отменена ({e})'
                        db.session.rollback()
                        return jsonify({'error': True, 'error_message': error_message})
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
                    fileType=file_type)
                new_message.files.append(newFile)
                current_user.files.append(newFile)
            except Exception as e:
                traceback.print_exc()
                error_message = f'при сохранении файла {attachment.filename}, отправка отменена ({e})'
                db.session.rollback()
                return jsonify({'error': True, 'error_message': error_message})
        current_user.last_judge = judge.id
        if sig_required:
            new_message.sigById = judge.id
            new_message.sigByName = judgeFio
        db.session.commit()
        try:
            all_files_signed = are_all_files_signed(new_message)
            if all_files_signed:
                new_message.signed = True
                export_signed_message(new_message)
                db.session.commit()
                sent_mails_in_current_session += "1"
                flash('Сообщение успешно отправлено.', category='success')
                return jsonify({'error': False, 'redirect_url': url_for('views.create_message')})
        except Exception as e:
            traceback.print_exc()
            error_message = f'при экспорте готового письма ({e}).'
            db.session.rollback()
            return jsonify({'error': True, 'error_message': error_message})
        sent_mails_in_current_session += "1"
        flash('Сообщение передано на подпись. После подписания будет отправлено.', category='success')
        return jsonify({'error': False, 'redirect_url': url_for('views.create_message')})
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        error_message = f'Ошибка {e}'
        return jsonify({'error': True, 'error_message': error_message})
    finally:
        db.session.close()


@api.post('/forward-existing-message')
@login_required
def forward_existing_message():
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        emails = data.get('emails').split(';')  # Преобразование строки адресов в список
        new_emails = process_emails2(emails)
        if not new_emails:
            return jsonify({'error': True, 'error_message': f'Не указан действительный email'})
        original_message = UploadedMessages.query.get(message_id)
        new_message = UploadedMessages(
            createDatetime=datetime.utcnow(),  # Устанавливаем текущее время создания
            signed=original_message.signed,
            sigById=original_message.sigById,
            sigByName=original_message.sigByName,
            toEmails=new_emails,  # Новые адреса для отправки
            mailSubject=f'Пересылка: {original_message.mailSubject}',
            mailBody=original_message.mailBody,
            user_id=original_message.user_id,
            thread_id=generate_new_thread_id())
        # Сохраняем новое сообщение в базу данных
        db.session.add(new_message)
        # Добавление файлов и подписей от исходного сообщения к новому сообщению
        new_message.files.extend(original_message.files)
        new_message.sigs.extend(original_message.sigs)
        db.session.commit()
        if new_message.signed:
            export_signed_message(new_message)
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': True, 'error_message': f'Произошла ошибка:{e}'})
    return jsonify({'error': False, 'error_message': 'Сообщение успешно переслано.'})


@api.post('/cancel-message')
@login_required
def cancel_message():
    msg_id = request.args.get('message_id', None, type=int)
    if msg_id is None:
        return jsonify({'error': True, 'error_message': 'ID сообщения не указан.'})
    msg = UploadedMessages.query.get(msg_id)
    if msg is None:
        return jsonify({'error': True, 'error_message': 'Сообщение не найдено.'})
    if msg.signed:
        error_message = 'Ошибка. Невозможно удалить отправленное сообщение.'
        return jsonify({'error': True, 'error_message': error_message})
    try:
        # Удаление файлов и связанных записей
        for file in msg.files:
            file_path = os.path.join(config['file_storage'], file.fileNameUUID)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(file)
        # Удаление подписей и связанных записей
        for sig in msg.sigs:
            sig_path = os.path.join(config['file_storage'], sig.sigNameUUID)
            if os.path.exists(sig_path):
                os.remove(sig_path)
            db.session.delete(sig)
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'error': False, 'error_message': 'Сообщение и связанные файлы успешно удалены.'}), 200
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': True, 'error_message': f'Произошла ошибка при удалении сообщения. {e}'}), 500


@api.get('/set-archived')
@login_required
def archive_message():
    try:
        msg_id = request.args.get('message_id', None, type=int)
        if msg_id is None:
            return jsonify({'error': True, 'error_message': 'ID сообщения не указан.'}), 400
        msg = UploadedMessages.query.get(msg_id)
        if msg is None:
            return jsonify({'error': True, 'error_message': 'Сообщение не найдено.'}), 400
        else:
            msg.archived = True
            db.session.commit()
            return jsonify({'error': False, 'error_message': 'Сообщение перемещено в архив'}), 200
    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify({'error': True, 'error_message': f'Ошибка выполнения запроса{e}'}), 400


@api.route('/convert_to_pdf', methods=['POST'])
def convert_to_pdf_route():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, file.filename)
            output_path = os.path.join(temp_dir, file.filename + '.pdf')
            file.save(input_path)
            convert_to_pdf(input_path, output_path)
            return send_file(output_path, as_attachment=True)
    except:
        traceback.print_exc()
        return "Error during conversion", 500


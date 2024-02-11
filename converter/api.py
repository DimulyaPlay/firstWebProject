import time
import traceback
from .auth import login
from flask import request, jsonify, Blueprint, make_response, send_file, render_template_string
from flask_login import current_user, login_required
from .models import UploadedFiles, UploadedMessages
from sqlalchemy import desc
from .Utils import analyze_file, config, generate_modal, sent_mails_in_current_session, check_sig, export_signed_message
import os
from . import db
import tempfile
import zipfile


api = Blueprint('api', __name__)


@api.route('/judge-files', methods=['GET'])
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


@api.route('/outbox-messages', methods=['GET'])
@login_required
def get_out_messages():
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
    total_files = len(filtered_messages)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_messages = filtered_messages[start_index:end_index]

    messages_data = []
    for message in paginated_messages:
        messages_data.append({
            'mailSubject': message.mailSubject,
            'createDatetime': message.createDatetime.isoformat(),
            'signed': message.signed,
            'id': message.id,
            'reportDatetime': message.reportDatetime,
            'toEmails': message.toEmails,
            'sigByName': message.sigByName,
            'toRosreestr': message.toRosreestr,
            'filesCount': len(message.files),
            'search_query': search_query
        })
    total_pages = (total_files + per_page - 1) // per_page
    start_index_pages = page - 3 if page - 3 > 1 else 1
    end_index_pages = page + 3 if page + 3 < total_pages else total_pages
    return jsonify({
        'messages': messages_data,
        'total_pages': total_pages,
        'current_page': page,
        "start_index_pages": start_index_pages,
        "end_index_pages": end_index_pages,
        'search': search_query
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


@api.route('/get-report', methods=['GET'])
@login_required
def get_report():
    msg_id = request.args.get('message_id', 1, type=int)
    msg = UploadedMessages.query.get(msg_id)
    report_filepath = os.path.join(config['file_storage'], msg.reportNameUUID)
    if os.path.exists(report_filepath):
        return send_file(report_filepath, as_attachment=False)
    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@api.route('/get-message-modal', methods=['GET'])
@login_required
def get_message_modal():
    msg_id = request.args.get('message_id', 1, type=int)
    msg = UploadedMessages.query.get(msg_id)
    modal = generate_modal(msg)
    return render_template_string(modal)


@api.route('/upload-signed-file', methods=['POST'])
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
                error_message = 'Ошибка: Подпись не прошла проверку.'
                return jsonify({'error': True, 'error_message': error_message})
        db.session.commit()
        message_files = UploadedFiles.query.filter_by(message_id=file.message_id).all()
        all_files_signed = all(file.sigName for file in message_files)
        if all_files_signed:
            message = UploadedMessages.query.filter_by(id=file.message_id).first()
            message.signed = True
            export_signed_message(message)
            db.session.commit()
        error_message = 'Файл успешно подписан.'
        return jsonify({'error': False, 'error_message': error_message})
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        error_message = f'Ошибка: {e}'
        return jsonify({'error': True, 'error_message': error_message})
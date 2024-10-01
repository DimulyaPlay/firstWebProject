from .Utils import create_new_message_from_zip, export_signed_message, delayed_file_removal, export_files_to_epr, api_key_required, config, are_all_files_signed
from .models import UploadedMessages, UploadedFiles, UploadedSigs
import tempfile
import os
import traceback
import shutil
import zipfile
from threading import Thread
from flask import request, jsonify, Blueprint, send_file, after_this_request, g
from sqlalchemy import desc, case, and_
from . import db

ext = Blueprint('ext', __name__)


@ext.get('/get-msg-messages_oa')
def get_msg_messages_oa():
    empty_msg_messages = UploadedMessages.query.filter(
        UploadedMessages.responseUUID.is_(None),
        UploadedMessages.signed.is_(True))
    messages_data = [message.id for message in empty_msg_messages if (message.toRosreestr or message.toEmails)]
    return jsonify({
        'messages': messages_data
    })


@ext.route('/upload-msg-report', methods=['POST'])
def upload_msg_report():
    print('Accepting report')
    try:
        filename = request.args.get('filename')
        print('Accepting report:', filename)
        with tempfile.TemporaryDirectory() as tmpdir:
            uploaded_file = request.files.get('file')
            filepath_to_save = os.path.join(tmpdir, filename)
            uploaded_file.save(filepath_to_save)
            res = create_new_message_from_zip(filepath_to_save)
            return jsonify({'error': False, 'error_message': 'Отчет прикреплен'}), 200
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        error_message = f'Ошибка: {e}'
        return jsonify({'error': True, 'error_message': error_message}), 400


@ext.get('/get-epr-messages_pm')
def get_epr_messages_pm():
    empty_toepr_messages = UploadedMessages.query.filter(
        UploadedMessages.toEpr.isnot(None),
        UploadedMessages.signed.is_(True),
        UploadedMessages.epr_uploadedUUID.is_(None)
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
        'epr_number': message.toEpr.split('|')[0],
        'epr_reason': status_mapping[message.toEpr.split('|')[1]],
        'epr_coment': message.toEpr.split('|')[2]
    } for message in empty_toepr_messages]
    return jsonify({'messages': messages_data})


@ext.get('/get-msg-file')
def get_msg_file():
    idx = request.args.get('message_id')
    message_obj = UploadedMessages.query.get(idx)
    tempdir = tempfile.mkdtemp()
    try:
        zip_for_export = export_signed_message(message_obj, tempdir)

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


@ext.route('/get-epr-file', methods=['GET'])
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


@ext.get('/judge-files')
@api_key_required
def get_judge_files():
    # Используем `g.user`, который был установлен в декораторе
    base_query = UploadedMessages.query.filter(UploadedMessages.sigById == g.user.id)
    # Фильтруем неподписанные файлы
    base_query = base_query.filter(
        ~UploadedMessages.files.any(UploadedFiles.signed==True)
    )
    files_data = []
    for message in base_query:
        for file in message.files:
            if file.sig_required:
                files_data.append({
                    'fileName': file.fileName,
                    'id': file.id,
                    'sigPages': file.sigPages
                })
    return jsonify({
        'files': files_data,
    })


@ext.route('/get-file', methods=['GET'])
@api_key_required
def get_file():
    idx = request.args.get('file_id', 1, type=int)
    file_obj = UploadedFiles.query.get(idx)
    if not file_obj:
        error_message = 'Ошибка: файл не найден в базе данных.'
        return jsonify({'error': True, 'error_message': error_message})
    file_path = os.path.join(config['file_storage'], file_obj.fileNameUUID)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        error_message = 'Ошибка: файл не найден в хранилище.'
        return jsonify({'error': True, 'error_message': error_message})


@ext.route('/upload-signed-file', methods=['POST'])
@api_key_required
def upload_signed_file():
    try:
        file_id = request.form['fileId']
        zip_file = request.files['file']
        file = UploadedFiles.query.get(file_id)

        if not file:
            return jsonify({'error': True, 'error_message': 'Файл не найден'})

        # Находим message_id на основе связей
        message = file.messages[0] if file.messages else None
        if not message:
            return jsonify({'error': True, 'error_message': 'Связанное сообщение не найдено'})

        # Дальнейшая обработка файла
        file_path = os.path.join(config['file_storage'], file.fileNameUUID)
        sig_name_uuid = file.fileNameUUID + '.sig'
        sig_path = os.path.join(config['file_storage'], sig_name_uuid)
        gf_file_path = os.path.join(config['file_storage'], f'gf_{file.fileNameUUID}')

        # Работа с загруженным zip-файлом
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

        # Проверка подписи
        if config['sig_check']:
            if not check_sig(file_path, sig_path):
                error_message = 'Ошибка: Подпись не прошла проверку.'
                return jsonify({'error': True, 'error_message': error_message})

        # Создание и добавление подписи
        new_sig = UploadedSigs(
            sigNameUUID=sig_name_uuid,
            sigName=file.fileName + '.sig'
        )
        message.sigs.append(new_sig)
        file.signature = new_sig
        file.signed = True

        if file.sigPages:
            file.gf_fileNameUUID = f'gf_{file.fileNameUUID}'

        db.session.commit()

        # Проверка подписания всех файлов в сообщении
        all_files_signed = are_all_files_signed(message)
        if all_files_signed:
            message.signed = True
            if os.path.isdir(config['file_export_folder']) and config['offline_export']:
                export_signed_message(message)
            db.session.commit()

        return jsonify({'error': False, 'error_message': 'Файл успешно подписан.'})

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        error_message = f'Ошибка: {e}'
        return jsonify({'error': True, 'error_message': error_message})

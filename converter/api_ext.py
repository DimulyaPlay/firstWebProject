from .Utils import create_new_message_from_zip, export_signed_message, delayed_file_removal
from .models import UploadedMessages
import tempfile
import os
import traceback
import shutil
from threading import Thread
from flask import request, jsonify, Blueprint, send_file
from . import db

ext = Blueprint('ext', __name__)


@ext.get('/get-msg-messages_oa')
def get_msg_messages_oa():
    empty_msg_messages = UploadedMessages.query.filter(
        UploadedMessages.responseUUID.is_(None),
        UploadedMessages.signed.is_(True),
        UploadedMessages.toEmails.isnot(None))
    messages_data = [message.id for message in empty_msg_messages]
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

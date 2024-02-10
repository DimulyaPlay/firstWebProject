import time
import traceback
from .auth import login
from flask import request, jsonify, Blueprint
from flask_login import current_user, login_required
from .models import UploadedFiles, UploadedMessages
from sqlalchemy import desc
from .Utils import analyze_file


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
    print(search_query)
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
        "end_index_pages": end_index_pages
    })


@api.route('/analyze-file', methods=['POST'])
@login_required
def analyzefile():
    file = request.files['file']
    detected_addresses = analyze_file(file)
    if detected_addresses:
        return jsonify(detectedAddresses=detected_addresses)
    else:
        return jsonify(error='No addresses detected in the file'), 400

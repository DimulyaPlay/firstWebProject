import time
import traceback
from flask import request, render_template, url_for, send_file, jsonify, Blueprint, flash, redirect
from flask_login import current_user, login_required, logout_user
from .models import UploadedFiles, UploadedMessages, Users
from sqlalchemy import desc
import os
from datetime import datetime, timedelta
from . import db, free_mails_limit
from .Utils import config, save_config, get_users_with_role, read_create_config, hwid, sent_mails_in_current_session, is_valid, get_server_ip, license_message, verify_license_key


views = Blueprint('views', __name__)


@views.route('/', methods=['GET'])
def home_redirector():
    if current_user.is_authenticated:
        if current_user.has_role(2):
            return redirect(url_for('views.judge_cabinet'))
        judges = get_users_with_role(2)
        return render_template('index.html', title='Отправить письмо', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Войти', user=current_user)


@views.route('/create_message', methods=['GET'])
def create_message():
    if current_user.is_authenticated:
        if not is_valid and len(sent_mails_in_current_session) > free_mails_limit:
            flash('Лимит сообщений исчерпан, новые сообщения отправляться не будут.', 'error')
        judges = get_users_with_role(2)
        return render_template('index.html', title='Отправить письмо', user=current_user, judges=judges)
    else:
        return render_template('login.html', title='Войти', user=current_user)


@views.route('/epr_cabinet', methods=['GET'])
def epr_cabinet():
    if current_user.is_authenticated:
        return render_template('epr.html', title='Кабинет ЭПР', user=current_user)
    else:
        return render_template('login.html', title='Войти', user=current_user)


@views.route('/judge_cabinet', methods=['GET'])
@login_required
def judge_cabinet():
    return render_template('judgecabinet.html', title='Кабинет судьи', user=current_user)


@views.route('/archive', methods=['GET'])
@login_required
def archive():
    return render_template('archive.html', title='Архив', user=current_user)


@views.route('/admin', methods=['GET'])
@login_required
def adminpanel():
    return render_template('adminpanel.html', title='Панель управления', user=current_user)


@views.route('/adminpanel/system', methods=['GET', 'POST'])
@login_required
def adminpanel_system():
    global config, license_message, is_valid
    if request.method == 'GET':
        return render_template('adminpanel_system.html',
                               title='Панель управления',
                               user=current_user,
                               default_configuration=config,
                               hwid=hwid,
                               license_message=license_message)
    if request.method == 'POST':
        try:
            sig_check = request.form.get('sig_check') == 'on'  # Преобразование в boolean
            csp_path = request.form.get('csp_path')
            file_storage = request.form.get('file_storage')
            file_export_folder = request.form.get('file_export_folder')
            reports_path = request.form.get('reports_path')
            soffice_path = request.form.get('soffice_path')
            if sig_check:
                if not os.path.exists(csp_path):
                    flash('Параметры не были сохранены, недействительный путь к Крипто Про', category='error')
                    return redirect(url_for('views.adminpanel_system'))
            if not all((os.path.exists(file_storage), os.path.exists(file_export_folder), os.path.exists(reports_path))):
                flash('Параметры не были сохранены, один или несколько из путей для хранения недоступны', category='error')
                return redirect(url_for('views.adminpanel_system'))
            l_key = request.form.get('l_key')
            is_valid, license_message = verify_license_key(l_key, hwid)
            config['sig_check'] = sig_check
            config['csp_path'] = csp_path
            config['file_storage'] = file_storage
            config['file_export_folder'] = file_export_folder
            config['soffice_path'] = soffice_path
            config['reports_path'] = reports_path
            config['auth_timeout'] = request.form.get('auth_timeout')
            config['l_key'] = l_key
            config['restricted_emails'] = request.form.get('restricted_emails')
            config['server_ip'] = request.form.get('server_ip', get_server_ip())
            config['server_port'] = request.form.get('server_port', 5000)
            config['msg_attachments_dir'] = request.form.get('msg_attachments_dir')
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
        users_table = Users.query.all()
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
                    user.fio = user_data.get('fio', user.fio)
                    user.login = user_data.get('login', user.login)
                    if user_data.get('judge'):
                        user.add_role(2)
                    else:
                        user.remove_role(2)
                    if user_data.get('reg'):
                        user.add_role(1)
                    else:
                        user.remove_role(1)
                    db.session.commit()
            return jsonify({'success': True, 'message': 'Параметры успешно сохранены'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Параметры не были сохранены: ' + str(e)})


@views.route('/outbox', methods=['GET'])
@login_required
def outbox():
    return render_template('outbox.html',
                           title='Мои отправления',
                           user=current_user)



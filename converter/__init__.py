import time

from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
import os
import sys
import shutil
from threading import Thread
from datetime import datetime, timedelta
from flask_migrate import Migrate
from uuid import uuid4
import hashlib


db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(basedir, 'instance', 'database.db')
local_tracking_db = os.path.join(basedir, 'instance', f"tracking_db_{uuid4().hex}.db")
soffice_path = os.path.join(basedir, 'tools', 'LibreOfficePortablePrevious', 'LibreOfficePortablePrevious.exe')
convert_types_list = ['doc', 'docx', 'odt', 'rtf']
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.mkdir(os.path.join(basedir, 'instance'))
free_mails_limit = 20


def create_app(config):
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        instance_path = os.path.join(sys._MEIPASS, 'instance')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder, instance_path=instance_path)
    else:
        app = Flask(__name__)
    app.config['SECRET_KEY'] = 'ndfjknsdflkghnfhjkgndbfd dfghmdghnm'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database_path + '?check_same_thread=False'
    if config['tracking_path']:
        if os.path.exists(config['tracking_path'] and config['tracking_path'].endswith('.db')):
            instance_path = os.path.join(basedir, 'instance')
            for filename in os.listdir(instance_path):
                if filename.startswith('tracking_db_'):
                    os.remove(os.path.join(instance_path, filename))
            shutil.copyfile(config['tracking_path'], local_tracking_db)
            app.config['SQLALCHEMY_BINDS'] = {
                'tracking_db': 'sqlite:///' + local_tracking_db + '?check_same_thread=False'
            }
            thread = Thread(target=switch_tracking_database, args=(app, config['tracking_path']), daemon=True)
            thread.start()
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
    #  кэширование ресурсов на стороне клиента
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=31536000)
    app.jinja_env.filters['versioned_static'] = lambda filename: url_for('static', filename=filename) + '?v=' + str(
        os.path.getmtime(os.path.join(app.static_folder, filename)))
    #  кэширование ресурсов на стороне клиента
    db.init_app(app)
    migrate = Migrate(app, db)
    from .views import views
    from .auth import auth
    from .api import api
    from .api_ext import ext
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(api, url_prefix='/api/')
    app.register_blueprint(ext, url_prefix='/ext/')
    from .models import Users, UploadedFiles
    create_db(app)
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    from .Utils import start_monitoring, process_existing_msg
    process_existing_msg(config['reports_path'],  app)
    Thread(target=start_monitoring, args=(config['reports_path'], app), daemon=True).start()

    @login_manager.user_loader
    def load_user(userid):
        return Users.query.get(int(userid))

    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            if int(config['auth_timeout']) and (current_user.last_seen < datetime.utcnow() - timedelta(
                    hours=int(config['auth_timeout']))):  # 2 часа неактивности
                logout_user()
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
    return app


def create_db(app):
    if not os.path.exists(database_path):
        with app.app_context():
            db.create_all()


def switch_tracking_database(app, new_db_path):

    while True:
        time.sleep(60*60)
        if os.path.exists(new_db_path) and new_db_path.endswith('.db'):
            instance_path = os.path.join(basedir, 'instance')
            temp_db_path = os.path.join(instance_path, f"tracking_db_{uuid4().hex}.db")
            old_db_path = app.config['SQLALCHEMY_BINDS'].get('tracking_db', None)
            old_db_file_path = old_db_path.replace('sqlite:///', '').split('?')[0] if old_db_path else None
            if old_db_file_path and compare_files(new_db_path, old_db_file_path):
                continue
            shutil.copyfile(new_db_path, temp_db_path)
            app.config['SQLALCHEMY_BINDS'] = {
                'tracking_db': 'sqlite:///' + temp_db_path + '?check_same_thread=False'
            }
            if old_db_file_path and os.path.exists(old_db_file_path):
                try:
                    os.remove(old_db_file_path)
                    print(f"База трекинга обновлена.")
                except Exception as e:
                    print(f"Ошибка при удалении старой базы данных: {e}")


def get_file_hash(file_path):
    """Возвращает хэш файла для проверки изменений."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compare_files(file1, file2):
    """Сравнивает два файла по их хэшу."""
    if not os.path.exists(file1) or not os.path.exists(file2):
        return False
    return get_file_hash(file1) == get_file_hash(file2)

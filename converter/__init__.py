from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
import os
import sys
from threading import Thread
from datetime import datetime, timedelta
from flask_migrate import Migrate

db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(basedir, 'instance', 'database.db')
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
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(api, url_prefix='/api/')
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

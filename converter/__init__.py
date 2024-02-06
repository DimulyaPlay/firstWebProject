from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import sys
from threading import Thread

db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(basedir, 'instance', 'database.db')
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
    db.init_app(app)
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    from .models import Users, UploadedFiles
    create_db(app)
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    from .Utils import start_monitoring, process_existing_reports
    process_existing_reports(config['reports_path'], config['file_storage'],  app)
    Thread(target=start_monitoring, args=(config['reports_path'], app), daemon=True).start()

    @login_manager.user_loader
    def load_user(userid):
        return Users.query.get(int(userid))
    return app


def create_db(app):
    if not os.path.exists(database_path):
        with app.app_context():
            db.create_all()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))
database_path = os.path.join(basedir, 'instance', 'database.db')


def create_app():
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

    @login_manager.user_loader
    def load_user(userid):
        return Users.query.get(int(userid))
    return app


def create_db(app):
    if not os.path.exists(database_path):
        with app.app_context():
            db.create_all()

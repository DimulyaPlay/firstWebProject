import datetime
from flask_login import UserMixin
from . import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    files = db.relationship('ProcessedFile')


class ProcessedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filenameStored = db.Column(db.String(120), unique=True, nullable=False)
    filenameUploaded = db.Column(db.String(120), unique=False, nullable=False)
    uploadedDate = db.Column(db.Date, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    toRosreestr = db.Column(db.Boolean, default=False)
    toEmails = db.Column(db.String(256), unique=False)
    reportData = db.Column(db.String(256), unique=False)


class Judge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(80), unique=True, nullable=False)
    inputStorage = db.Column(db.String(255), nullable=False)
    outputStorage = db.Column(db.String(255), nullable=False)

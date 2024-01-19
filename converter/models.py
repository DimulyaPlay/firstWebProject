from datetime import datetime
from flask_login import UserMixin
from . import db


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    last_judge = db.Column(db.String(80), nullable=True, default=None)
    judge_id = db.Column(db.Integer)
    files = db.relationship('UploadedFiles', backref='user', lazy=True)
    messages = db.relationship('UploadedMessages', backref='user', lazy=True)


class Judges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(80), unique=True, nullable=False)
    files = db.relationship('UploadedFiles', backref='judge', lazy=True)


class UploadedMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # время создания письма
    signed = db.Column(db.Boolean, default=False)  # подписано ли
    sigBy = db.Column(db.String(120), default=None)  # Подписано кем ФИО
    toRosreestr = db.Column(db.Boolean)  # Флаг отправки в росреестр
    toEmails = db.Column(db.String(255))  # Адреса отправки на почту, '' = не отправлять
    mailSubject = db.Column(db.String(255))  # Тема письма для отправки
    mailBody = db.Column(db.Text)  # Тело сообщения
    reportDatetime = db.Column(db.DateTime, default=None)  # время подгрузки отчета об отправке по эл почте
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # внешний ключ для Users.id


class UploadedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # Время загрузки документа
    filePath = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненному файлу
    fileName = db.Column(db.String(255), nullable=False)  # Название файла
    sigPages = db.Column(db.String(120), default=None)  # Предложенные страницы для размещения штампа
    sigPath = db.Column(db.String(255), unique=True, default=None)  # Путь к сохраненной подписи
    sigName = db.Column(db.String(255), default=None)  # Название файла подписи
    sigBy = db.Column(db.String(120), default=None)  # Подписано кем ФИО, если None, то подписи не требует (аттачмент)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # связь файла с пользователем по ИД
    judge_id = db.Column(db.Integer, db.ForeignKey('judges.id'), default=None)  # связь файла с судьей по ИД
    message_id = db.Column(db.Integer, db.ForeignKey('uploaded_messages.id'))  # внешний ключ для UploadedMessages.id
    message = db.relationship('UploadedMessages', backref='file', lazy=True)

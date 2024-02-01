from datetime import datetime
from flask_login import UserMixin
from . import db


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # время создания письма
    is_judge = db.Column(db.Boolean, default=False)
    fio = db.Column(db.String(80), unique=True, default=None)
    first_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    last_judge = db.Column(db.String(80), nullable=True, default=None)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    files = db.relationship('UploadedFiles', backref='user', lazy=True)
    messages = db.relationship('UploadedMessages', backref='user', lazy=True)


class UploadedMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # время создания письма
    signed = db.Column(db.Boolean, default=False)  # подписано ли
    sigBy = db.Column(db.String(120), default=None)  # Подписано кем ФИО
    reportDatetime = db.Column(db.DateTime, default=None)  # время подгрузки отчета
    reportNameUUID = db.Column(db.String(255), default=None)  # путь к файлу отчета
    reportName = db.Column(db.String(255), default=None)  # имя файла отчета
    toRosreestr = db.Column(db.Boolean)  # Флаг отправки в росреестр
    toEmails = db.Column(db.String(255))  # Адреса отправки на почту, '' = не отправлять
    mailSubject = db.Column(db.String(255))  # Тема письма для отправки
    mailBody = db.Column(db.Text)  # Тело сообщения
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # внешний ключ для Users.id


class UploadedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # Время загрузки документа
    fileNameUUID = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненному файлу
    fileName = db.Column(db.String(255), nullable=False)  # Название файла
    fileType = db.Column(db.String(50))  # Расширение файла
    sigPages = db.Column(db.String(120), default=None)  # Предложенные страницы для размещения штампа
    sigNameUUID = db.Column(db.String(255), unique=True, default=None)  # Путь к сохраненной подписи
    sigName = db.Column(db.String(255), default=None)  # Название файла подписи
    sigBy = db.Column(db.String(120), default=None)  # Подписано кем ФИО, если None, то подписи не требует (аттачмент)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # связь файла с пользователем по ИД
    message_id = db.Column(db.Integer, db.ForeignKey('uploaded_messages.id'))  # внешний ключ для UploadedMessages.id
    message = db.relationship('UploadedMessages', backref='files', lazy=True)

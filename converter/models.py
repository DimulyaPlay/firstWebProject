import datetime
from flask_login import UserMixin
from . import db


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    last_judge = db.Column(db.String(80), unique=False, nullable=True, default='')
    files = db.relationship('UploadedFiles')
    messages = db.relationship('UploadedMessages')


class UploadedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    uploadedDate = db.Column(db.Date, default=datetime.datetime.utcnow)  # Время загрузки документа
    filePath = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненному файлу
    fileName = db.Column(db.String(255), unique=False, nullable=False)  # Название файла
    sigPages = db.Column(db.String(120), unique=True, default='')  # Предложенные страницы для размещения штампа
    sigPath = db.Column(db.String(255), unique=True, default='')  # Путь к сохраненной подписи
    sigName = db.Column(db.String(255), unique=True, default='')  # Название файла подписи
    sigBy = db.Column(db.String(120), unique=True, default='')  # Подписано кем (Название сертификата)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # связь файла с пользователем по ИД
    judge_id = db.Column(db.Integer, db.ForeignKey('judges.id'))  # связь файла с судьей по ИД


class UploadedMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    toRosreestr = db.Column(db.Boolean, default=False)  # Флаг отправки в росреестр
    toEmails = db.Column(db.String(255), unique=False)  # Адреса отправки на почту, '' = не отправлять
    mailSubject = db.Column(db.String(255), unique=False)  # Тема письма для отправки
    messageBody = db.Column(db.Text)  # Тело сообщения
    sentDatetime = db.Column(db.Date)  # время отправки файла по указанным реквизитам
    reportDatetime = db.Column(db.Date)  # время подгрузки отчета об отправке по эл почте
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # связь файла с пользователем по ИД


class Judges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(80), unique=True, nullable=False)
    inputStorage = db.Column(db.String(255), nullable=False)
    outputStorage = db.Column(db.String(255), nullable=False)
    files = db.relationship('UploadedFiles')

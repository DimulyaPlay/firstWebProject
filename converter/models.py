from datetime import datetime
from flask_login import UserMixin
from . import db


files_messages_association = db.Table('files_messages',
    db.Column('file_id', db.Integer, db.ForeignKey('uploaded_files.id'), primary_key=True),
    db.Column('message_id', db.Integer, db.ForeignKey('uploaded_messages.id'), primary_key=True)
)


# Вспомогательная таблица для связи подписей и сообщений
sigs_messages_association = db.Table('sigs_messages',
    db.Column('sig_id', db.Integer, db.ForeignKey('uploaded_sigs.id'), primary_key=True),
    db.Column('message_id', db.Integer, db.ForeignKey('uploaded_messages.id'), primary_key=True)
)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # время создания пользователя
    roles = db.Column(db.String(8), default='0')  # Храним роли как строку  # 0 отправитель, 1 регистратор, 2 судья
    fio = db.Column(db.String(80), unique=True, nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    last_judge = db.Column(db.String(80), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    files = db.relationship('UploadedFiles', backref='user', lazy=True)
    messages = db.relationship('UploadedMessages', backref='user', lazy=True)

    def has_role(self, role):
        return str(role) in self.roles

    def add_role(self, role):
        if not self.has_role(role):
            self.roles += str(role)

    def remove_role(self, role):
        if self.has_role(role):
            self.roles = self.roles.replace(str(role), '')


class Notifications(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(256), nullable=False)
    user = db.relationship('Users', backref='notifications', lazy=True)


class ExternalSenders(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID внешнего отправителя
    email = db.Column(db.String(255), nullable=False, unique=True)  # Email внешнего отправителя
    messages = db.relationship('UploadedMessages', backref='external_sender', lazy=True)  # Связь с сообщениями


class UploadedMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # время создания письма
    signed = db.Column(db.Boolean, default=False)  # подписано ли
    sigById = db.Column(db.Integer, nullable=True)  # Подписано кем ИД
    sigByName = db.Column(db.String(80), default='-')  # Подписано кем ФИО
    description = db.Column(db.String(255), nullable=True)
    archived = db.Column(db.Boolean, default=False)  # Сообщение находится в архиве
    toRosreestr = db.Column(db.Boolean, default=False)  # Флаг отправки в росреестр
    toEmails = db.Column(db.String(255), nullable=True)  # Адреса отправки на почту, '' = не отправлять
    toEpr = db.Column(db.String(32), )  # Ответ на обращение на портале Эпр
    mailSubject = db.Column(db.String(255))  # Тема письма для отправки
    mailBody = db.Column(db.Text, nullable=True)  # Тело сообщения
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # внешний ключ для Users.id
    external_sender_id = db.Column(db.Integer, db.ForeignKey('external_senders.id'),
                                   nullable=True)  # внешний ключ для ExternalSenders.id
    is_responsed = db.Column(db.Boolean, default=False)  # Является ли сообщение ответом на другое сообщение
    is_incoming = db.Column(db.Boolean, default=False)  # Является ли сообщение входящим
    is_declined = db.Column(db.Boolean, default=False)  # Возникла ли ошибка при отправке
    thread_id = db.Column(db.Integer, nullable=False)  # Идентификатор цепочки сообщений
    responseUUID = db.Column(db.String(255), unique=True, nullable=True)  # Путь к файлу отчета
    epr_uploadedUUID = db.Column(db.String(255), unique=True, nullable=True)  # Путь к файлу отчета
    rr_uploadedUUID = db.Column(db.String(255), unique=False, nullable=True)  # Путь к файлу отчета PP
    files = db.relationship('UploadedFiles', secondary=files_messages_association, lazy='subquery',
                            backref=db.backref('messages', lazy=True))
    sigs = db.relationship('UploadedSigs', secondary=sigs_messages_association, lazy='subquery',
                           backref=db.backref('messages', lazy=True))


class UploadedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # Время загрузки документа
    fileNameUUID = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненному файлу
    fileName = db.Column(db.String(255), nullable=False, unique=False)  # Название файла
    fileType = db.Column(db.String(16), nullable=False)  # Расширение файла
    gf_fileNameUUID = db.Column(db.String(255), unique=True, nullable=True)  # Путь к сохраненному файлу
    sig_required = db.Column(db.Boolean, default=False)
    signed = db.Column(db.Boolean, default=False)  # подписано ли
    sigPages = db.Column(db.String(16))  # Предложенные страницы для размещения штампа
    signature = db.relationship('UploadedSigs', uselist=False, backref='file', lazy=True)  # отношение один к одному
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # внешний ключ для Users.id


class UploadedSigs(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # Время загрузки документа
    sigNameUUID = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненной подписи
    sigName = db.Column(db.String(255), nullable=False)  # Название файла подписи
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'))  # внешний ключ для UploadedFiles.id


class UploadedAttachments(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID
    createDatetime = db.Column(db.DateTime, default=datetime.utcnow)  # Время загрузки документа
    fileNameUUID = db.Column(db.String(255), unique=True, nullable=False)  # Путь к сохраненному файлу
    hashSum = db.Column(db.String(255), unique=True, nullable=False)  # Хэшсумма
    fileType = db.Column(db.String(16), nullable=False)  # Расширение файла


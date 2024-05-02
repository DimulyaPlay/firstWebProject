import glob
import os
import sys
import re
from PyPDF2 import PdfReader
import subprocess
from .models import UploadedFiles, UploadedMessages
from . import db
import zipfile
import json
from datetime import datetime
from uuid import uuid4
import traceback
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from email_validator import validate_email
import time
import jwt

sk = 'Ваш hwid:'
try:
    if os.name == 'nt':
        from wmi import WMI
        hwid = WMI().Win32_ComputerSystemProduct()[0].UUID
    elif os.name == 'posix':
        process = subprocess.Popen(['sudo', 'dmidecode', '-s', 'system-serial-number'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        hwid = out.strip().decode()  # Преобразуем bytes в str и удаляем лишние пробелы
    else:
        hwid = 'Ваша операционная система не поддерживается.'
    if hwid:
        print('Ваш HWID:', hwid)
except Exception as e:
    hwid = 'Ошибка.'
    print('Не удалось получить ваш HWID:', e)

sent_mails_in_current_session = ''

config_path = os.path.dirname(sys.argv[0])
if not os.path.exists(config_path):
    os.mkdir(config_path)
config_file = os.path.join(config_path, 'config.json')


def read_create_config(config_filepath=config_file):
    default_configuration = {
        "sig_check": False,
        "csp_path": r"C:\Program Files\Crypto Pro\CSP",
        "file_storage": r"C:\fileStorage",
        "file_export_folder": r"C:\fileStorage\Export",
        "reports_path": r"C:\fileStorage\Reports",
        'auth_timeout': 0,
        'l_key': "",
        'restricted_emails': ''
    }
    if os.path.exists(config_filepath):
        try:
            with open(config_filepath, 'r') as configfile:
                cfg = json.load(configfile)
                for key, value in default_configuration.items():
                    if key not in list(cfg.keys()):
                        cfg[key] = default_configuration[key]
                for fp in ("file_storage", "file_export_folder", "reports_path"):
                    if not os.path.exists(cfg[fp]):
                        os.mkdir(cfg[fp])
        except Exception as e:
            traceback.print_exc()
            os.remove(config_filepath)
            cfg = default_configuration
            with open(config_filepath, 'w') as configfile:
                json.dump(cfg, configfile)
    else:
        cfg = default_configuration
        with open(config_filepath, 'w') as configfile:
            json.dump(cfg, configfile)
    return cfg


def verify_license_key(license_key, current_hwid):
    try:
        decoded = jwt.decode(license_key, sk, algorithms=["HS256"])
        if decoded["hwid"] != current_hwid:
            return False, "ID оборудования не соответствует ключу, доступо 20 писем за сессию."
        return True, "Валидный ключ"
    except jwt.ExpiredSignatureError as e:
        print(e)
        return False, "Ключ истек, доступо 20 писем за сессию."
    except jwt.InvalidTokenError as e:
        print(e)
        return False, "Невалидный ключ, доступо 20 писем за сессию."
    except Exception as e:
        print(e)
        return False, "Неизвестная ошибка, доступо 20 писем за сессию."


config = read_create_config(config_file)
is_valid, license_message = verify_license_key(config['l_key'], hwid)
print(license_message)


def save_config():
    try:
        global config
        with open(config_file, 'w') as json_file:
            json.dump(config, json_file)
    except:
        traceback.print_exc()


def analyze_file(file):
    try:
        if file.filename.endswith('.pdf'):
            pdf_reader = PdfReader(file)
            content = ''
            for page_num in range(1):
                content += pdf_reader.pages[page_num].extract_text().lower().replace(' ', '')
            detected_addresses = analyze_text(content)
        else:
            return []
        return detected_addresses
    except Exception:
        traceback.print_exc()
        return []


def analyze_text(text):
    try:
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        matches = email_pattern.findall(text)
        matches = [match for match in matches]
        detected_addresses = [address for address in matches if not address.lower() in config['restricted_emails'].split(';')]
        return detected_addresses
    except Exception as e:
        traceback.print_exc()
        return []


def process_emails(request_form):
    toEmails = True if request_form.get('sendByEmail') == 'on' else None
    if toEmails:
        emails = '; '.join([email for email in request_form.getlist('email') if validate_email(email) and email.lower() not in config['restricted_emails'].split(';')])
        return emails if emails else None
    return None


def process_emails2(emails_list):
    val_mails = []
    for email in emails_list:
        try:
            validate_email(email)
            if email not in config['restricted_emails'].split(';'):
                val_mails.append(email)
        except:
            traceback.print_exc()
    emails = '; '.join(val_mails)
    return emails if emails else None


def generate_sig_pages(current_list, custom_string):
    print(current_list, custom_string)
    input_pagelist = get_sorted_pages(custom_string)
    current_set = set(current_list)
    current_set.update(input_pagelist)
    print(current_set)
    return ",".join(map(str, sorted(current_set)))


def get_sorted_pages(chosen_pages_string):
    out_set = set()
    chosen_pages_string = chosen_pages_string.replace(' ', '')
    if chosen_pages_string:
        string_lst = chosen_pages_string.split(',')
        for i in string_lst:
            try:
                if '-' in i:
                    start, end = map(int, i.split('-'))
                    out_set.update(range(start, end + 1))
                else:
                    out_set.add(int(i))
            except ValueError:
                pass  # Ignoring non-integer values
        return out_set
    else:
        return []


def check_sig(fp, sp):
    if os.path.exists(fp) and os.path.exists(sp):
        command = [
            config['csp_path'] + '\\csptest.exe',
            "-sfsign",
            "-verify",
            "-in",
            fp,
            "-signature",
            sp,
            "-detached",
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding='cp866',
                                creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.returncode
        return not output


def export_signed_message(message):
    zip_filename = os.path.join(config['file_export_folder'],
                                f'Export_msg_id_{message.id}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.zip')
    zip_filename_part = zip_filename + '.part'

    files = UploadedFiles.query.filter_by(message_id=message.id).all()
    filepaths = [os.path.join(config['file_storage'], f.fileNameUUID) for f in files]
    filenames = [f.fileName for f in files]
    filenames = [f'file_{i}' if filenames.count(f) > 1 else f for i, f in enumerate(filenames)]

    sigpaths = [os.path.join(config['file_storage'], f.sigNameUUID) for f in files if f.sigNameUUID]
    signames = [f.sigName for f in files]
    signames = [f'file_{i}' if signames.count(f) > 1 else f for i, f in enumerate(signames)]
    signames = [signame for signame in signames if signame != "No_need"]
    fileNames = filenames.copy()
    if sigpaths:
        fileNames.extend(signames)

    meta = {
        'id': message.id,
        'rr': message.toRosreestr,
        'emails': message.toEmails,
        'subject': message.mailSubject,
        'body': message.mailBody,
        'fileNames': fileNames
    }
    with zipfile.ZipFile(zip_filename_part, 'w') as zip_file:
        for file_path, file_name in zip(filepaths, filenames):
            zip_file.write(file_path, arcname=file_name)
        if sigpaths:
            for file_path, file_name in zip(sigpaths, signames):
                zip_file.write(file_path, arcname=file_name)
        meta_filename = 'meta.json'
        with open(meta_filename, 'w') as meta_file:
            json.dump(meta, meta_file)
        zip_file.write(meta_filename, arcname=meta_filename)
    os.remove(meta_filename)
    os.rename(zip_filename_part, zip_filename)
    return zip_filename


class ReportHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        global config
        if event.is_directory:
            return
        with self.app.app_context():
            filename = os.path.basename(event.src_path)
            if filename == 'SOEDkey.txt':
                time.sleep(1)
                with open(event.src_path) as file:
                    l_key = file.readline()
                    res, msg = verify_license_key(license_key=l_key, current_hwid=hwid)
                    if res:
                        config['l_key'] = l_key
                        save_config()
                os.remove(event.src_path)
                return
            is_reply = False
            message_id = filename.split('.')[0]  # функция для извлечения ID из названия файла
            if filename.split('.')[1] == 'reply':
                is_reply = True
            new_filename = str(uuid4()) + '.pdf'
            new_filepath = os.path.join(config['file_storage'], new_filename)
            time.sleep(2)
            shutil.move(event.src_path, new_filepath)
            message = UploadedMessages.query.get(message_id)
            if message:
                if not is_reply:
                    message.reportDatetime = datetime.utcnow()
                    message.reportNameUUID = new_filename
                    message.reportName = filename
                    db.session.commit()
                else:
                    message.replyDatetime = datetime.utcnow()
                    message.replyNameUUID = new_filename
                    message.replyName = filename
                    db.session.commit()


def start_monitoring(path, app):
    event_handler = ReportHandler(app)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    print('reports monitoring started')
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


def process_existing_reports(directory, file_storage, app):
    with app.app_context():
        existing_files = glob.glob(directory + '/*.pdf')
        for fp in existing_files:
            is_reply = False
            filename = os.path.basename(fp)
            message_id = filename.split('.')[0]  # функция для извлечения ID из названия файла
            if filename.split('.')[1] == 'reply':
                is_reply = True
            new_filename = str(uuid4()) + '.pdf'
            new_filepath = os.path.join(file_storage, new_filename)
            time.sleep(1)
            shutil.move(fp, new_filepath)
            message = UploadedMessages.query.get(message_id)
            if message:
                if not is_reply:
                    message.reportDatetime = datetime.utcnow()
                    message.reportNameUUID = new_filename
                    message.reportName = filename
                    db.session.commit()
                else:
                    message.replyDatetime = datetime.utcnow()
                    message.replyNameUUID = new_filename
                    message.replyName = filename
                    db.session.commit()


def generate_modal_message(message):
    files_list_html = ""
    for file in message.files:
        download_link = f'<a href="/api/get-file?file_id={file.id}" target="_blank">{file.fileName}</a>'
        # Проверка наличия электронной подписи
        signature_link = f'<a href="/api/get-sign?file_id={file.id}" target="_blank">(подписано УКЭП)</a>' if file.sigNameUUID else ''
        files_list_html += f"<li>{download_link} {signature_link}</li>"

    replies_list_html = ""
    for reply in message.replies:
        ...

    # Форматирование даты и времени
    report_datetime = message.reportDatetime.strftime("%Y-%m-%d %H:%M:%S") if message.reportDatetime else "Нет"

    # Добавляем разметку для поля ввода адресов электронной почты
    email_input_html = """
    <div id="emailSection" class="mb-2">
        <div class="tags-input-wrapper mb-2">
            <div id="emailTags" class="tags-container"></div>
        </div>
        <input type="email" id="emailInput" class="form-control"
            placeholder="Введите адрес и нажмите Enter">
    </div>
    """

    modal = f"""
    <div class="modal fade message-modal" id="myModal{message.id}" data-message-id="{message.id}" tabindex="-1" role="dialog" aria-labelledby="myModalLabel{message.id}" aria-hidden="true">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="myModalLabel{message.id}">Письмо №{message.id}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Создано: <span data-utc-time="{message.createDatetime}"></span></p>
                    <div class="mb-3">
                        <label for="mailSubject" class="form-label">Тема:</label>
                        <div id="mailSubject" class="form-control" style="height: auto; white-space: pre-wrap;">{message.mailSubject}</div>
                    </div>
                    <div class="mb-3">
                        <label for="mailBody" class="form-label">Содержание:</label>
                        <div id="mailBody" class="form-control" style="height: auto; white-space: pre-wrap;">{message.mailBody}</div>
                    </div>
                    <p>Отправлять в Росреестр: {"Да" if message.toRosreestr else "Нет"}</p>
                    <p>Отправлять по email: {message.toEmails if message.toEmails else "Нет"}</p>
                    <p>Время подгрузки отчета: <span data-utc-time="{message.reportDatetime}">{report_datetime}</span></p>
                    <h6>Файлы:</h6>
                    <ul>{files_list_html}</ul>
                    {email_input_html}
                </div>
                <div class="modal-footer">
                    {f"<a href='#' class='btn btn-primary forward-message'>Переслать на указанные адреса</a>"}
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>  
                </div>
            </div>
        </div>
    </div>
    """
    return modal


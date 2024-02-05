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
from wmi import WMI
try:
    hwid = WMI().Win32_ComputerSystemProduct()[0].UUID
    print('Ваш HWID:', hwid)
except:
    print('Не удалось получить ваш HWID')


config_path = os.path.dirname(sys.argv[0])
if not os.path.exists(config_path):
    os.mkdir(config_path)
config_file = os.path.join(config_path, 'config.json')


def read_create_config(config_filepath=config_file):
    default_configuration = {
        "sig_check": True,
        "csp_path": r"C:\Program Files\Crypto Pro\CSP",
        "file_storage": r"C:\fileStorage",
        "file_export_folder": r"C:\fileStorage\Export",
        "reports_path": r"C:\fileStorage\Reports",
        'auth_timeout': 0,
        'l_key': ""
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


config = read_create_config(config_file)


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
            return []  # Неподдерживаемый формат файла
        return detected_addresses
    except Exception as e:
        traceback.print_exc()
        return []


def analyze_text(text):
    try:
        email_pattern = re.compile(r'\[([^\]]+@[^\]]+)\]')
        matches = email_pattern.findall(text)
        matches = [match for match in matches]
        detected_addresses = matches
        detected_addresses = [address for address in detected_addresses if validate_email(address)]
        return detected_addresses
    except Exception as e:
        traceback.print_exc()
        return []


def process_emails(request_form):
    toEmails = True if request_form.get('sendByEmail') == 'on' else None
    if toEmails:
        emails = '; '.join([email for email in request_form.getlist('email') if validate_email(email)])
        return emails if emails else None
    return None


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

    files = UploadedFiles.query.filter_by(message_id=message.id).all()
    filepaths = [f.filePath for f in files]
    filenames = [f.fileName for f in files]
    filenames = [f'file_{i}' if filenames.count(f) > 1 else f for i, f in enumerate(filenames)]

    sigpaths = [f.sigPath for f in files if f.sigPath]
    signames = [f.sigName for f in files]
    signames = [f'file_{i}' if signames.count(f) > 1 else f for i, f in enumerate(signames)]
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
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
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
    return zip_filename


def report_exists(message_id):
    report_filepath = os.path.join(config['reports_path'], f'{message_id}.pdf')
    return os.path.exists(report_filepath)


class ReportHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if event.is_directory:
            return
        with self.app.app_context():
            filename = os.path.basename(event.src_path)
            message_id = filename.split('.')[0]  # функция для извлечения ID из названия файла
            new_filename = str(uuid4()) + '.pdf'
            new_filepath = os.path.join(config['file_storage'], new_filename)
            time.sleep(1)
            shutil.move(event.src_path, new_filepath)
            message = UploadedMessages.query.get(message_id)
            if message:
                message.reportDatetime = datetime.utcnow()
                message.reportFilepath = new_filepath
                message.reportFilename = new_filename
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
        # Теперь весь код здесь выполняется в контексте приложения Flask
        existing_files = glob.glob(directory + '/*.pdf')
        for fp in existing_files:
            filename = os.path.basename(fp)
            message_id = filename.split('.')[0]  # функция для извлечения ID из названия файла
            new_filename = str(uuid4()) + '.pdf'
            new_filepath = os.path.join(file_storage, new_filename)
            time.sleep(1)
            shutil.move(fp, new_filepath)
            message = UploadedMessages.query.get(message_id)
            if message:
                message.reportDatetime = datetime.utcnow()
                message.reportFilepath = new_filepath
                message.reportFilename = new_filename
                db.session.commit()


def generate_modal(message):
    # Формирование списка файлов для данного сообщения
    files_list_html = ""
    for file in message.files:
        download_link = f'<a href="/get_file?file_id={file.id}" target="_blank">{file.fileName}</a>'
        files_list_html += f"<li>{download_link}</li>"

    # Форматирование даты и времени
    created_at = message.createDatetime.strftime("%Y-%m-%d %H:%M:%S")
    report_datetime = message.reportDatetime.strftime("%Y-%m-%d %H:%M:%S") if message.reportDatetime else "Нет"

    modal = f"""
    <div class="modal fade" id="myModal{message.id}" tabindex="-1" role="dialog" aria-labelledby="myModalLabel{message.id}" aria-hidden="true">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="myModalLabel{message.id}">Письмо №{message.id}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Создано: <span data-utc-time="{message.createDatetime}">{created_at}</span></p>
                    <div class="mb-3">
                        <label for="mailBody" class="form-label">Тема:</label>
                        <div id="mailBody" class="form-control" style="height: auto; white-space: pre-wrap;">{message.mailSubject}</div>
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
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                </div>
            </div>
        </div>
    </div>
    """
    return modal


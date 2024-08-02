import glob
import os
import sys
import re
import tempfile
from PyPDF2 import PdfReader
import subprocess
from .models import UploadedFiles, UploadedMessages, UploadedSigs, Users, UploadedAttachments, ExternalSenders
from . import db, free_mails_limit
from sqlalchemy import func
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
import textwrap
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
import extract_msg
from msgtopdf import Msgtopdf
import hashlib
import socket
import re

font_path = os.path.join(os.path.dirname(sys.argv[0]), 'converter', 'ttf.ttf')
pdfmetrics.registerFont(TTFont('ttf', font_path))
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


def get_server_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address


def read_create_config(config_filepath=config_file):
    default_configuration = {
        "sig_check": False,
        "csp_path": r"C:\Program Files\Crypto Pro\CSP",
        "file_storage": r"C:\fileStorage",
        "file_export_folder": r"C:\fileStorage\Export",
        "reports_path": r"C:\fileStorage\Reports",
        'soffice_path': r'C:\Program Files\LibreOffice\program',
        'auth_timeout': 0,
        'l_key': "",
        'restricted_emails': '',
        'server_ip': get_server_ip(),
        'server_port': 5000,
        'msg_attachments_dir': r"C:\fileStorage\MsgAttachments"
    }
    if os.path.exists(config_filepath):
        try:
            with open(config_filepath, 'r') as configfile:
                cfg = json.load(configfile)
                for key, value in default_configuration.items():
                    if key not in list(cfg.keys()):
                        cfg[key] = default_configuration[key]
                for fp in ("file_storage", "file_export_folder", "reports_path", 'msg_attachments_dir'):
                    if not os.path.exists(cfg[fp]):
                        os.mkdir(cfg[fp])
        except Exception as e:
            traceback.print_exc()
            os.remove(config_filepath)
            cfg = default_configuration
            with open(config_filepath, 'w') as configfile:
                json.dump(cfg, configfile, indent=4)
    else:
        cfg = default_configuration
        with open(config_filepath, 'w') as configfile:
            json.dump(cfg, configfile, indent=4)
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


def convert_to_pdf(input_file, output_file):
    output_dir = os.path.dirname(output_file)
    command = [
        os.path.join(config['soffice_path'], 'soffice.exe'),
        '--headless',
        '--convert-to',
        'pdf',
        input_file,
        '--outdir',
        output_dir
    ]
    try:
        print(command)
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.returncode == 0:
            generated_pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + '.pdf')
            if os.path.exists(generated_pdf):
                shutil.move(generated_pdf, output_file)
                os.remove(input_file)
                return output_file
            else:
                raise Exception("Generated PDF file not found")
        else:
            raise Exception(f"Conversion failed: {result.stderr}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error during conversion: {e.stderr}")


def save_config():
    try:
        global config
        with open(config_file, 'w') as json_file:
            json.dump(config, json_file, indent=4)
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

def delayed_file_removal(file_list, delay=5):
    time.sleep(delay)
    for file_path in file_list:
        try:
            while os.path.exists(file_path):
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                    print(file_path, 'removed')
                    break
                except PermissionError:
                    time.sleep(1)
        except Exception as e:
            print(f'Error removing file {file_path}: {e}')


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
        emails = '; '.join([email for email in request_form.getlist('email') if email.lower() not in config['restricted_emails'].split(';')])
        return emails if emails else None
    return None


def process_description(request_form):
    mainDescriprion = request_form.get('mainDescription')
    toEpr = request_form.get('eprNumber')
    toRosreestr = request_form.get('toRosreestr')
    mailSubject = request_form.get('subject')
    if mainDescriprion:
        return mainDescriprion
    elif mailSubject:
        return mailSubject
    elif toEpr:
        return f'Ответ на обращение {toEpr}'
    elif toRosreestr:
        return 'Отправка в Росреестр'
    else:
        return 'Нет описания'


def process_epr(request_form):
    toEpr = request_form.get('sendToEpr') == 'on'
    if toEpr:
        epr_number = request_form.get('eprNumber')
        epr_status = request_form.get('eprStatus')
        epr_comment = request_form.get('eprComment')
        status_mapping = {
            'response': 0,
            'returned_for_corrections': 1,
            'returned_without_consideration': 2
        }
        status_number = status_mapping.get(epr_status, 0)
        if status_number is not None:
            toEprString = f"{epr_number}|{status_number}|{epr_comment}"
            return toEprString
        else:
            return None
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


def process_files(request_files):
    files_data = request_files.lists()
    new_files_data = {}
    for key, value in files_data:
        if key != 'attachments' and value[0].filename:
            new_files_data[key] = value[0]
    attachments = request_files.getlist('attachments')
    attachments = [attachment for attachment in attachments if attachment.filename]
    return new_files_data, attachments


def get_users_with_role(role_id):
    role_str = str(role_id)
    return Users.query.filter(Users.roles.like(f'%{role_str}%')).all()


def generate_new_thread_id():
    max_thread_id = db.session.query(func.max(UploadedMessages.thread_id)).scalar()
    if max_thread_id is None:
        return 1
    return max_thread_id + 1


def extract_thread_id(subject):
    match = re.search(r'.*\[tid-(\d+)-(\d+)\].*', subject)
    if match:
        return match.group(1), match.group(2)
    return None


def are_all_files_signed(message):
    return all(file.signed for file in message.files if file.sig_required)


def make_unique_filenames(names):
    counts = {}
    unique_names = []
    for name in names:
        if name in counts:
            counts[name] += 1
            unique_name = f"{name} ({counts[name]})"
        else:
            counts[name] = 0
            unique_name = name
        unique_names.append(unique_name)
    return unique_names


def export_signed_message(message, tempdir=None):
    export_folder = config['file_export_folder'] if os.path.isdir(config['file_export_folder']) else tempdir
    zip_filename = os.path.join(export_folder, f'Export_msg_id_{message.id}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.zip')
    zip_filename_part = zip_filename + '.part'
    files = message.files
    filepaths = [os.path.join(config['file_storage'], f.fileNameUUID) for f in files]
    filenames = [f.fileName for f in files]
    filenames = make_unique_filenames(filenames)
    ## добавими файлы с графическими подписями, если такие есть
    for fp in files:
        if fp.gf_fileNameUUID:
            gf_filepath = os.path.join(config['file_storage'], fp.gf_fileNameUUID)
            gf_filename = "gf_"+fp.fileName
            if os.path.exists(gf_filepath) and os.path.isfile(gf_filepath):
                filepaths.append(gf_filepath)
                filenames.append(gf_filename)
    sigs = message.sigs
    sigpaths = [os.path.join(config['file_storage'], f.sigNameUUID) for f in sigs if f.sigNameUUID]
    signames = [f.sigName for f in sigs]
    signames = make_unique_filenames(signames)
    fileNames = filenames.copy()
    if sigpaths:
        fileNames.extend(signames)

    meta = {
        'id': message.id,
        'thread': message.thread_id,
        'rr': message.toRosreestr,
        'emails': message.toEmails,
        'subject': message.mailSubject,
        'body': message.mailBody,
        'fileNames': fileNames
    }
    # Создание ZIP архива
    with zipfile.ZipFile(zip_filename_part, 'w') as zip_file:
        for file_path, file_name in zip(filepaths, filenames):
            zip_file.write(file_path, arcname=file_name)
        for file_path, file_name in zip(sigpaths, signames):
            zip_file.write(file_path, arcname=file_name)
        meta_filename = 'meta.json'
        with open(meta_filename, 'w') as meta_file:
            json.dump(meta, meta_file, indent=4)
        zip_file.write(meta_filename, arcname=meta_filename)
    os.remove(meta_filename)
    os.rename(zip_filename_part, zip_filename)
    return zip_filename


def export_files_to_epr(message, temp_dir):
    zip_filename = os.path.join(temp_dir,
                                f'Response_{message.toEpr}_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.zip')
    files = message.files
    filepaths = [os.path.join(config['file_storage'], f.fileNameUUID) for f in files]
    filenames = [f.fileName for f in files]
    filenames = make_unique_filenames(filenames)
    sigs = message.sigs
    sigpaths = [os.path.join(config['file_storage'], f.sigNameUUID) for f in sigs if f.sigNameUUID]
    signames = [f.sigName for f in sigs]
    signames = make_unique_filenames(signames)
    fileNames = filenames.copy()
    if sigpaths:
        fileNames.extend(signames)
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        for file_path, file_name in zip(filepaths, filenames):
            zip_file.write(file_path, arcname=file_name)
        for file_path, file_name in zip(sigpaths, signames):
            zip_file.write(file_path, arcname=file_name)
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
            if filename.endswith('.zip'):
                print('found', filename)
                time.sleep(2)
                res = create_new_message_from_zip(event.src_path)
                if not res:
                    print('failure on adding:', event.src_path)
                else:
                    os.remove(event.src_path)
            if filename.startswith('epr-') and filename.endswith('.pdf'):
                from api import upload_epr_report
                res = upload_epr_report(event.src_path)
                if not res:
                    print('failure on adding report:', event.src_path)


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


def process_existing_msg(directory, app):
    with app.app_context():
        existing_msgs = glob.glob(directory + '/*.zip')
        for msg in existing_msgs:
            res = create_new_message_from_zip(msg)
            if not res:
                print('failure on adding:', msg)
            else:
                os.remove(msg)
        existing_epr = glob.glob(directory + '/*.pdf')
        for epr in existing_epr:
            from api import upload_epr_report
            res = upload_epr_report(epr)
            if not res:
                print('failure on adding report:', epr)


def generate_modal_message(message):
    files_list_html = "Нет</h6>"
    if message.files:
        files_list_html = '</h6><ul>'
    for file in message.files:
        download_link = f'<a href="/api/get-file?file_id={file.id}" target="_blank">{file.fileName}</a>'
        # Проверка наличия электронной подписи
        signature_link = f'<a href="/api/get-sign?file_id={file.id}" target="_blank">(подписано УКЭП)</a>' if file.signed else ''
        gf_link = f'<a href="/api/get-gf?file_id={file.id}" target="_blank">(Документ со штампом)</a>' if file.gf_fileNameUUID else ''
        files_list_html += f"<li>{download_link} {signature_link} {gf_link}</li>"
    if message.files:
        files_list_html += '</ul>'

    message_sent_report = "Отчет не загружен"
    if message.responseUUID:
        message_sent_report = f'<a href="/api/get-report?message_id={message.id}" target="_blank">Открыть отчет об отправке</a>'
    to_email_form = 'Нет</p>'
    if message.toEmails:
        to_email_form = f'''</p>
        <ul>
            <li>Тема: {message.mailSubject}</li>
            <li>Тело: {message.mailBody if message.mailBody else 'Пусто'}</li>
            <li>Получатели: {message.toEmails}</li>
            <li>{message_sent_report}</li>
        </ul>'''

    epr_report_link_html = 'Отчет не загружен'
    if message.epr_uploadedUUID:
        epr_report_link_html = f'<a href="/api/get-epr-report?message_id={message.id}" target="_blank">Открыть отчет об отправке</a>'
    to_epr_form = 'Нет</p>'
    if message.toEpr:
        status_mapping = {
            '0': 'Ответ',
            '1': 'Возвращено для устр. недост.',
            '2': 'Возвращено без рассмотрения'
        }
        to_epr_values = message.toEpr.split('|')
        number = to_epr_values[0]
        response_type = status_mapping[to_epr_values[1]]
        comment = to_epr_values[2]
        to_epr_form = f'''</p>
        <ul>
            <li>Номер: {number}</li>
            <li>Вид ответа: {response_type}</li>
            <li>Комментарий: {comment}</li>
            <li>{epr_report_link_html}</li>
        </ul>'''

    thread_messages = UploadedMessages.query.filter_by(thread_id=message.thread_id).order_by(
        UploadedMessages.createDatetime).all()
    # Создаем HTML для сообщений в цепочке
    messages_list_html = ""
    for msg in thread_messages[1:]:
        # Получение первого файла в сообщении, если он существует
        first_file = msg.files[0] if msg.files else None
        if first_file:
            subject_link = f'<a href="/api/get-file?file_id={first_file.id}" target="_blank">{msg.description}</a>'
        else:
            subject_link = msg.description
        messages_list_html += f"""
            <div class="message-header">
            <span class="message-date" data-utc-time="{msg.createDatetime}"></span>
            <span class="message-subject">{subject_link}</span>
            </div>
        """
    # HTML для спойлера
    thread_spoiler_html = f"""
    <div class="accordion" id="accordionExample{message.id}">
        <div class="accordion-item">
            <h2 class="accordion-header" id="headingOne{message.id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne{message.id}" aria-expanded="false" aria-controls="collapseOne{message.id}">
                    Показать ответы на сообщение
                </button>
            </h2>
            <div id="collapseOne{message.id}" class="accordion-collapse collapse" aria-labelledby="headingOne{message.id}" data-bs-parent="#accordionExample{message.id}">
                <div class="accordion-body">
                    {messages_list_html}
                </div>
            </div>
        </div>
    </div>
    """

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
        <div class="modal-dialog modal-lg" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="myModalLabel{message.id}">Письмо №{message.id}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p><h6>Создано:</h6> <span data-utc-time="{message.createDatetime}"></span></p>
                    <div class="mb-3">
                        <h6 for="mailDesc" class="form-label">Описание отправления:</h6>
                        <div id="mailDesc" class="form-control" style="height: auto; white-space: pre-wrap;">{message.description}</div>
                    </div>
                    <h6>Файлы:
                    {files_list_html}
                    <h6>Отправка в:</h6>
                    <p>Росреестр: {"Да" if message.toRosreestr else "Нет"}</p>
                    <p>Email:
                    {to_email_form}
                    <p>ЭПР:
                    {to_epr_form}
                    <h6>Переслать сообщение на другие адреса:</h6>
                    {email_input_html}
                    {thread_spoiler_html}
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


def create_new_message_from_zip(msg_zip_path):
    try:
        pdf_path, thread_id, message_id, subject, sender_email = create_note_from_msg_zip(msg_zip_path)
        if not pdf_path:
            print(f'ERROR in file {pdf_path} for {thread_id}-{message_id}')
            return False
        else:
            print(f'generated file {pdf_path} for {thread_id}-{message_id}')
        # Если это отчет, то просто прикрепляем полученный пдф к оригинальному письму
        if os.path.basename(msg_zip_path).startswith('report'):
            msg_id = int(message_id)
            sent_msg = UploadedMessages.query.get(msg_id)
            fileNameUUID = str(uuid4()) + '.pdf'
            new_filepath_to_save = os.path.join(config['file_storage'], fileNameUUID)
            shutil.move(pdf_path, new_filepath_to_save)
            sent_msg.responseUUID = fileNameUUID
            db.session.commit()
            return True
        if os.path.basename(msg_zip_path).startswith('declined'): ## отклоненный архив
            msg_id = int(message_id)
            sent_msg = UploadedMessages.query.get(msg_id)
            sent_msg.is_declined = True
        # Иначе создаем новое входящее письмо
        sender = ExternalSenders.query.filter_by(email=sender_email).first()
        if not sender:
            sender = ExternalSenders(email=sender_email)
            db.session.add(sender)
            db.session.commit()

        new_message = UploadedMessages(
            mailSubject=subject,
            description=subject,
            external_sender_id=sender.id,
            is_incoming=True,
            thread_id=thread_id
        )
        db.session.add(new_message)
        orig_message = UploadedMessages.query.get(message_id)
        orig_message.is_responsed = True
        db.session.commit()
        fileNameUUID = str(uuid4()) + '.pdf'
        new_filepath_to_save = os.path.join(config['file_storage'], fileNameUUID)
        shutil.move(pdf_path, new_filepath_to_save)
        new_file = UploadedFiles(
            fileNameUUID=fileNameUUID,
            fileName=os.path.basename(pdf_path),
            fileType='pdf'
        )
        db.session.add(new_file)
        new_message.files.append(new_file)
        db.session.commit()
        return True
    except:
        traceback.print_exc()
        db.session.rollback()
        return False


def create_note_from_msg_zip(zip_path):
    """
    Создание PDF документа из Zip архива с сообщением и вложениями.
    @param zip_path: путь к Zip архиву
    @return: путь к созданному PDF файлу
    """
    print('Agregating message', zip_path)
    temp_dir = os.path.join(os.path.dirname(zip_path) ,str(uuid4()))
    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(temp_dir)
    print('Zip extracted')
    meta_path = os.path.join(temp_dir, 'meta.json')
    with open(meta_path, 'r', encoding='utf-8') as meta_file:
        meta = json.load(meta_file)
    print('Meta read')
    subject = meta.get('subject', '')
    thread_id, message_id = extract_thread_id(subject)
    max_line_length = 75
    subject_lines = textwrap.wrap(subject, max_line_length)
    res_date = meta.get('date', '')
    rec_list = meta.get('recipients', [])
    rec_str = ', '.join(rec_list)
    rec_lines = textwrap.wrap(rec_str, max_line_length)
    sender_str = meta.get('sender', '')
    body_text = meta.get('body', '').replace('\r', '').replace('\n\n', '\n')
    attachments = meta.get('attachments', {})
    pdf_path = f"{zip_path}.pdf"
    print('Creating', pdf_path)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("ttf", 8)
    x_offset = 25
    x_offset_val = 100
    y_current = 800
    c.drawString(x_offset, y_current, "От:")
    c.drawString(x_offset_val, y_current, sender_str)
    y_current -= 14
    c.drawString(x_offset, y_current, "Отправлено:")
    c.drawString(x_offset_val, y_current, res_date)
    y_current -= 14
    c.drawString(x_offset, y_current, "Кому:")
    for line in rec_lines:
        c.drawString(x_offset_val, y_current, line)
        y_current -= 14
    c.drawString(x_offset, y_current, "Тема:")
    for line in subject_lines:
        c.drawString(x_offset_val, y_current, line)
        y_current -= 14
    c.drawString(x_offset, y_current, "Вложения:")
    for file_uuid, original_name in attachments.items():
        file_path = os.path.join(temp_dir, file_uuid)
        filename_uuid = save_attachment(file_path)
        link_url = f"https://{config['server_ip']}:{config['server_port']}/api/get_attachment/{filename_uuid}"
        c.drawString(x_offset_val, y_current, original_name)
        c.linkURL(link_url, (x_offset_val, y_current, x_offset_val + 200, y_current + 10))
        y_current -= 14
    y_current -= 14
    c.drawString(x_offset, y_current, "Тело письма:")
    y_current -= 18
    text_object = c.beginText(x_offset, y_current)
    text_object.setFont("ttf", 8)
    text_object.setTextOrigin(x_offset, y_current)
    text_object.textLines(body_text)
    c.drawText(text_object)
    c.save()
    if os.path.exists(pdf_path):
        shutil.rmtree(temp_dir)
        return pdf_path, thread_id, message_id, subject, sender_str
    else:
        return '', '', '', '', ''


def save_attachment(file_path):
    print(file_path)
    hash_sum = calculate_md5(file_path)
    existing_file = UploadedAttachments.query.filter_by(hashSum=hash_sum).first()
    if existing_file:
        return existing_file.fileNameUUID
    filename_uuid = os.path.basename(file_path)
    file_extension = filename_uuid.split('.')[-1]
    save_directory = os.path.join(config['msg_attachments_dir'], filename_uuid)
    shutil.move(file_path, save_directory)
    new_attachment = UploadedAttachments(
        fileNameUUID=filename_uuid,
        hashSum=hash_sum,
        fileType=file_extension)
    db.session.add(new_attachment)
    db.session.commit()
    return filename_uuid


def calculate_md5(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

import os, sys, json, re
from PyPDF2 import PdfReader
import subprocess
from .models import UploadedFiles
import zipfile
import json
from datetime import datetime
from uuid import uuid4


config_path = os.path.dirname(sys.argv[0])
if not os.path.exists(config_path):
    os.mkdir(config_path)
config_file = os.path.join(config_path, 'config.json')


def read_create_config(config_file):
    default_configuration = {
        "sig_check": True,
        "csp_path": r"C:\Program Files\Crypto Pro\CSP",
        "file_storage": r"C:\fileStorage",
        "file_export_folder": r"C:\fileStorage\Export",
        "reports_path": r"C:\fileStorage\Reports"
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as configfile:
                config = json.load(configfile)
        except Exception as e:
            print(e)
            os.remove(config_file)
            config = default_configuration
            with open(config_file, 'w') as configfile:
                json.dump(config, configfile)
    else:
        config = default_configuration
        with open(config_file, 'w') as configfile:
            json.dump(config, configfile)
    return config


config = read_create_config(config_file)


def save_config(config):
    try:
        with open(config_file, 'w') as json_file:
            json.dump(config, json_file)
        config = read_create_config(config_file)
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
        print(f"An error occurred during file analysis: {str(e)}")
        return []


def analyze_text(text):
    try:
        email_pattern = re.compile(r'\[([^\]]+@[^\]]+)\]')
        matches = email_pattern.findall(text)
        matches = [match for match in matches]
        detected_addresses = matches
        return detected_addresses
    except Exception as e:
        print(f"An error occurred during text analysis: {str(e)}")
        return []


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


def report_exists(messageId):
    report_filepath = os.path.join(config['reports_path'], f'{messageId}.pdf')
    return os.path.exists(report_filepath)


def save_file(file, attachment=False):
    try:
        file_extension = "." + attachment.filename.rsplit('.', 1)[-1] if attachment else '.pdf'
        filepath = os.path.join(config['file_storage'], str(uuid4()) + file_extension)
        file.save(filepath)
        return filepath
    except Exception as e:
        raise ValueError(f'Ошибка при сохранении файла {file.filename}: {e}')

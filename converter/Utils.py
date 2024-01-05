import re
from PyPDF2 import PdfReader


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
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

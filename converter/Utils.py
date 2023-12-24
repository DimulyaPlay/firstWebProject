

def create_note_from_msg(subject, sentdate, rec_str, att_str, sender_str) -> object:
    """
    Создание из msg файла отдельного pdf документа(для печати не через outlook)
    Генерирует word документ по шаблону, затем конвертирует в pdf
    @param msg_path: путь к мсг
    @return: путь к пдф
    """
    msg = extract_msg.openMsg(msg_path)
    max_line_length = 75
    subject_lines = textwrap.wrap(subject, max_line_length)
    res_date = sentdate
    date_obj = datetime.datetime.strptime(res_date, "%a, %d %b %Y %H:%M:%S %z")
    res_date = date_obj.strftime("%d.%m.%Y, %H:%M:%S")
    rec_lines = textwrap.wrap(rec_str, max_line_length)
    att_lines = textwrap.wrap(att_str, max_line_length)
    att_lines = att_lines if att_lines else ['Вложений нет']
    body_text = str(msg.body).replace('\r', '').replace('\n\n', '\n')
    pdf_path = f"{msg_path}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=A4)
    pdfmetrics.registerFont(TTFont('Times', 'assets/times.ttf'))
    c.setFont("Times", 12)
    x_offset = 25
    x_offset_val = 100
    y_current = 800
    c.drawString(x_offset, y_current, "Отправитель:")
    c.drawString(x_offset_val, y_current, sender_str)
    y_current -= 18
    c.drawString(x_offset, y_current, "Получено:")
    c.drawString(x_offset_val, y_current, res_date)
    y_current -= 18
    c.drawString(x_offset, y_current, "Получатели:")
    for line in rec_lines:
        c.drawString(x_offset_val, y_current, line)
        y_current -= 18
    c.drawString(x_offset, y_current, "Тема:")
    for line in subject_lines:
        c.drawString(x_offset_val, y_current, line)
        y_current -= 18
    c.drawString(x_offset, y_current, "Вложения:")
    for line in att_lines:
        c.drawString(x_offset_val, y_current, line)
        y_current -= 18
    c.drawString(x_offset, y_current, "Тело письма:")
    y_current -= 25
    text_object = c.beginText(x_offset, y_current)
    text_object.setTextOrigin(x_offset, y_current)
    text_object.textLines(body_text)
    c.drawText(text_object)
    c.save()
    tempfile_list_for_delete.append(pdf_path)
    msg_document = Document(pdf_path, subject)
    msg_document.is_msg = True
    return msg_document
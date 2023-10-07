import time
import os
import traceback


def process_file(file_path):
    # Здесь происходит обработка файла (ваша логика обработки)
    # В данном примере просто ждем 10 секунд для имитации обработки
    time.sleep(5)
    new_filepath = file_path+'ready'
    return file_path, f'Processed {file_path}'


def file_cleaner(processed_files):
    while True:
        time.sleep(300)
        for key in list(processed_files.keys()):
            if time.time() - processed_files[key]['created'] > 1800:
                try:
                    os.remove(processed_files[key]['processed_file_path'])
                    del processed_files[key]
                except:
                    traceback.print_exc()

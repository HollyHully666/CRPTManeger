from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import sys  # Импортируем модуль sys для проверки, запущен ли скрипт как .exe
import os  # Импортируем модуль os для работы с операционной системой

def create_output_structure() -> dict:  # Определяем функцию create_output_structure, которая возвращает словарь
    # Путь к директории .exe
    if getattr(sys, 'frozen', False):  # Проверяем, запущен ли скрипт как .exe (атрибут frozen есть в PyInstaller)
        base_dir = Path(sys.executable).parent / "source"  # Если .exe, задаём base_dir как родительский каталог .exe + папка "source"
    else:  # Если скрипт запущен как .py
        base_dir = Path("source")  # Задаём base_dir как папка "source" в текущем каталоге

    uploaded_pdf_dir = base_dir / "ЗагруженныеPDF"  # Создаём путь для папки "ЗагруженныеPDF" внутри base_dir
    data_matrix_dir = base_dir / "DATA MATRIX"  # Создаём путь для папки "DATA MATRIX" внутри base_dir
    reports_dir = base_dir.parent / "ИТОГ" / "Отчеты о нанесении"  # Создаём путь для папки "Отчеты о нанесении" внутри "ИТОГ" (родитель base_dir)
    input_dir = base_dir.parent / "ИТОГ" / "Ввод в оборот"  # Создаём путь для папки "Ввод в оборот" внутри "ИТОГ" (родитель base_dir)
    upd_dir = base_dir.parent / "ИТОГ" / "Для УПД"  # Создаём путь для папки "Для УПД" внутри "ИТОГ" (родитель base_dir)

    for directory in [base_dir, uploaded_pdf_dir, data_matrix_dir, reports_dir, input_dir, upd_dir]:  # Цикл по списку всех созданных путей
        directory.mkdir(parents=True, exist_ok=True)  # Создаём каждую папку, если она не существует (parents=True создаёт родительские папки, exist_ok=True не выдаёт ошибку, если папка уже есть)

    return {  # Возвращаем словарь с путями к созданным папкам
        "uploaded_pdf": uploaded_pdf_dir,  # Ключ "uploaded_pdf" с путём к папке "ЗагруженныеPDF"
        "data_matrix": data_matrix_dir,  # Ключ "data_matrix" с путём к папке "DATA MATRIX"
        "reports": reports_dir,  # Ключ "reports" с путём к папке "Отчеты о нанесении"
        "input_folder": input_dir,  # Ключ "input_folder" с путём к папке "Ввод в оборот"
        "upd_folder": upd_dir  # Ключ "upd_folder" с путём к папке "Для УПД"
    }  # Закрывающая скобка возвращаемого словаря
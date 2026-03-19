from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import sys  # Импортируем модуль sys для проверки, запущен ли скрипт как .exe
import os  # Импортируем модуль os для работы с операционной системой

def create_output_structure() -> dict:  # Определяем функцию create_output_structure, которая возвращает словарь
    # Путь к директории .exe
    if getattr(sys, 'frozen', False):  # Проверяем, запущен ли скрипт как .exe (атрибут frozen есть в PyInstaller)
        base_dir = Path(sys.executable).parent / "source"  # Если .exe, задаём base_dir как родительский каталог .exe + папка "source"
    else:  # Если скрипт запущен как .py
        base_dir = Path("source")  # Задаём base_dir как папка "source" в текущем каталоге

    uploaded_pdf_dir = base_dir / "ЗагруженныеPDF"
    data_matrix_dir = base_dir / "DATA MATRIX"
    full_codes_dir = base_dir.parent / "ИТОГ" / "Полные коды"  # Сырые коды сразу после сканирования
    reports_dir = base_dir.parent / "ИТОГ" / "Отчеты о нанесении"
    input_dir = base_dir.parent / "ИТОГ" / "Ввод в оборот"
    upd_dir = base_dir.parent / "ИТОГ" / "Для УПД"

    for directory in [base_dir, uploaded_pdf_dir, data_matrix_dir, full_codes_dir, reports_dir, input_dir, upd_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "uploaded_pdf": uploaded_pdf_dir,
        "data_matrix": data_matrix_dir,
        "full_codes": full_codes_dir,
        "reports": reports_dir,
        "input_folder": input_dir,
        "upd_folder": upd_dir,
    }
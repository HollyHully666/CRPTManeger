from pathlib import Path
import logging
import logging.handlers
from datetime import datetime
import shutil
import tkinter as tk
from tkinter import filedialog
from typing import List

from Modules.createOutputStructure import create_output_structure
from Modules.pdf_to_png import convert_pdf_to_images
from Modules.decode_datamatrix import extract_datamatrix_from_image
from Modules.format_kiz_code import format_kiz_code
from Modules.get_product_data import get_product_data
from Modules.generate_final_csv import generate_final_csv
import pandas as pd

def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger = logging.getLogger()
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

def select_pdf_files() -> List[Path]:
    root = tk.Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(title="Выберите PDF-файлы", filetypes=[("PDF files", "*.pdf")])
    root.destroy()
    return [Path(p) for p in file_paths]

def copy_pdf_to_uploaded_dir(pdf_files: List[Path], uploaded_pdf_dir: Path) -> None:
    uploaded_pdf_dir.mkdir(parents=True, exist_ok=True)
    for item in uploaded_pdf_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    for pdf_file in pdf_files:
        try:
            dest_path = uploaded_pdf_dir / pdf_file.name
            shutil.copy(pdf_file, dest_path)
        except Exception as e:
            logging.error(f"Ошибка при копировании {pdf_file}: {e}")

def clear_source_dir(source_dir: Path) -> None:
    try:
        if source_dir.exists():
            shutil.rmtree(source_dir)
            logging.info(f"Папка {source_dir} очищена")
        create_output_structure()
        logging.info(f"Папка {source_dir} пересоздана")
    except Exception as e:
        logging.error(f"Ошибка при очистке {source_dir}: {e}")

def clear_itog_subdirs(input_dir: Path, reports_dir: Path, upd_dir: Path) -> None:
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    for dir_path in [input_dir, reports_dir, upd_dir]:
        try:
            if dir_path.exists():
                for item in dir_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                logging.info(f"Содержимое папки {dir_path} очищено")
        except Exception as e:
            logging.error(f"Ошибка при очистке {dir_path}: {e}")

def save_to_xlsx(formatted_codes: dict, input_dir: Path):
    for pdf_name, codes in formatted_codes.items():
        df = pd.DataFrame(codes, columns=["Код"])
        xlsx_path = input_dir / f"{pdf_name}.xlsx"
        df.to_excel(xlsx_path, index=False)

def save_to_csv(extracted_codes: dict, reports_dir: Path):
    for pdf_name, codes in extracted_codes.items():
        df = pd.DataFrame(codes, columns=["Код"])
        csv_path = reports_dir / f"{pdf_name}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")

def main():
    try:
        paths = create_output_structure()
        uploaded_pdf_dir = paths["uploaded_pdf"]
        data_matrix_dir = paths["data_matrix"]
        reports_dir = paths["reports"]
        input_dir = paths["input_folder"]
        upd_dir = paths["upd_folder"]
        source_dir = uploaded_pdf_dir.parent
        setup_logging(source_dir)
        clear_itog_subdirs(input_dir, reports_dir, upd_dir)
    except Exception as e:
        logging.error(f"Не удалось создать структуру папок: {e}. Выход из программы")
        return

    pdf_files = select_pdf_files()
    if not pdf_files:
        logging.error("Не выбрано ни одного PDF-файла. Завершение работы")
        return

    copy_pdf_to_uploaded_dir(pdf_files, uploaded_pdf_dir)

    POPPLER_BIN_PATH = r"C:\Tools\poppler\Library\bin"

    logging.info("Конвертация PDF в PNG...")
    try:
        processed_pdfs_info = convert_pdf_to_images(uploaded_pdf_dir=uploaded_pdf_dir, data_matrix_dir=data_matrix_dir, poppler_path=POPPLER_BIN_PATH)
        if not processed_pdfs_info:
            logging.error("Не удалось конвертировать PDF-файлы. Завершение работы")
            return
        logging.info(f"Конвертировано PDF: {len(processed_pdfs_info)} файлов")
    except Exception as e:
        logging.error(f"Ошибка при конвертации PDF: {e}. Завершение работы")
        return

    choice = input("Что хотите получить на выходе?\n (1) Файлы для Ввода в оборот\n (2) Файлы для отчета о нанесении\n (3) Шаблон для загрузки УПД\n (4) Все сразу\n (Укажите через пробел, например: 1 3):\n ")
    choices = [int(x) for x in choice.split() if x.isdigit()]
    if not choices:
        logging.error("Неверный ввод. Завершение работы")
        return

    if 4 in choices:
        choices = [1, 2, 3]
        logging.info("Выбран вариант 4: выполнение всех действий")

    logging.info("Распознавание DataMatrix-кодов...")
    try:
        write_reports = 2 in choices
        extracted_codes_by_pdf = extract_datamatrix_from_image(data_matrix_dir=data_matrix_dir, reports_dir=reports_dir, write_reports=write_reports)
        if not extracted_codes_by_pdf:
            logging.error("Не удалось извлечь DataMatrix-коды. Завершение работы")
            return
        logging.info(f"Извлечено кодов: {sum(len(codes) for codes in extracted_codes_by_pdf.values())}")
    except Exception as e:
        logging.error(f"Ошибка при извлечении кодов: {e}. Завершение работы")
        return

    formatted_codes = {}
    code_types = {}
    if 1 in choices or 3 in choices:
        logging.info("Форматирование КИЗ-кодов...")
        try:
            write_input = 1 in choices
            write_upd = 3 in choices
            formatted_codes, code_types = format_kiz_code(extracted_codes_by_pdf=extracted_codes_by_pdf, input_dir=input_dir, upd_dir=upd_dir, include_short_codes=True, write_input=write_input, write_upd=write_upd)
            if not formatted_codes:
                logging.error("Форматирование не вернуло данных. Завершение работы")
                return
        except Exception as e:
            logging.error(f"Ошибка при форматировании кодов: {e}. Завершение работы")
            return

    if 1 in choices:
        save_to_xlsx(formatted_codes, input_dir)
        logging.info(f"Сохранено в XLSX в {input_dir}")

    if 2 in choices:
        save_to_csv(extracted_codes_by_pdf, reports_dir)
        logging.info(f"Сохранено в CSV в {reports_dir}")

    if 3 in choices:
        logging.info("Запрос данных о товарах...")
        try:
            product_data = get_product_data(uploaded_pdf_dir=uploaded_pdf_dir, reports_dir=reports_dir, extracted_codes_by_pdf=extracted_codes_by_pdf, code_types=code_types)
            if not product_data:
                logging.error("Не получены данные о товарах. Завершение работы")
                return
        except Exception as e:
            logging.error(f"Ошибка при запросе данных о товарах: {e}. Завершение работы")
            return

        logging.info("Генерация итогового CSV...")
        try:
            output_csv_path = upd_dir / "final_upd.csv"
            generate_final_csv(reports_dir=reports_dir, upd_dir=upd_dir, output_path=output_csv_path)
        except Exception as e:
            logging.error(f"Ошибка при создании CSV: {e}. Завершение работы")
            return

    logging.info("Программа успешно завершена")
    if 3 in choices:
        logging.info(f"Итоговый CSV: {output_csv_path}")

    clear_source_dir(source_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Программа прервана пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        paths = create_output_structure()
        source_dir = paths["uploaded_pdf"].parent
        clear_source_dir(source_dir)
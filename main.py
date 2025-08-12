from pathlib import Path  # Импорт Path для работы с путями файловой системы
import logging  # Модуль для логирования
import logging.handlers  # Дополнительные обработчики логов (например, ротация файлов)
from datetime import datetime  # Дата и время для меток и имён файлов
import shutil  # Операции с файлами и папками (копирование, удаление)
import tkinter as tk  # Библиотека Tkinter для GUI
from tkinter import filedialog  # Диалог выбора файлов
from typing import List  # Аннотация типа: список

from Modules.createOutputStructure import create_output_structure  # Создание структуры выходных папок
from Modules.pdf_to_png import convert_pdf_to_images  # Конвертация PDF в изображения PNG
from Modules.decode_datamatrix import extract_datamatrix_from_image  # Извлечение DataMatrix-кодов с изображений
from Modules.format_kiz_code import format_kiz_code  # Форматирование КИЗ-кодов
from Modules.get_product_data import get_product_data  # Получение данных о товарах
from Modules.generate_final_csv import generate_final_csv  # Генерация итогового CSV для УПД
import pandas as pd  # Работа с табличными данными

def setup_logging(log_dir: Path) -> None:  # Настройка логирования (консоль + файл с ротацией)
    log_dir.mkdir(parents=True, exist_ok=True)  # Создаём директорию для логов, если её нет
    log_file = log_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"  # Имя файла лога с меткой времени
    logger = logging.getLogger()  # Получаем корневой логгер
    if not logger.handlers:  # Добавляем обработчики только один раз
        logger.setLevel(logging.INFO)  # Устанавливаем уровень логирования INFO
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Формат сообщения лога
        console_handler = logging.StreamHandler()  # Обработчик вывода в консоль
        console_handler.setFormatter(log_format)  # Применяем формат для консоли
        logger.addHandler(console_handler)  # Регистрируем обработчик консоли
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)  # Файловый обработчик с ротацией
        file_handler.setFormatter(log_format)  # Применяем формат для файла
        logger.addHandler(file_handler)  # Регистрируем файловый обработчик

def select_pdf_files() -> List[Path]:  # Диалог выбора PDF-файлов, возвращает список путей
    root = tk.Tk()  # Создаём корневое окно Tkinter
    root.withdraw()  # Скрываем главное окно, чтобы не мешало
    file_paths = filedialog.askopenfilenames(title="Выберите PDF-файлы", filetypes=[("PDF files", "*.pdf")])  # Диалог выбора нескольких PDF
    root.destroy()  # Уничтожаем окно после выбора
    return [Path(p) for p in file_paths]  # Преобразуем строки в объекты Path

def copy_pdf_to_uploaded_dir(pdf_files: List[Path], uploaded_pdf_dir: Path) -> None:  # Копирование выбранных PDF в служебную папку
    uploaded_pdf_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку, если её нет
    for item in uploaded_pdf_dir.iterdir():  # Очищаем папку от предыдущего содержимого
        if item.is_file():  # Если это файл — удаляем
            item.unlink()
        elif item.is_dir():  # Если это поддиректория — удаляем рекурсивно
            shutil.rmtree(item)
    for pdf_file in pdf_files:  # Перебираем все выбранные PDF
        try:
            dest_path = uploaded_pdf_dir / pdf_file.name  # Путь, куда копировать
            shutil.copy(pdf_file, dest_path)  # Копируем файл
        except Exception as e:
            logging.error(f"Ошибка при копировании {pdf_file}: {e}")  # Логируем любую ошибку копирования

def clear_source_dir(source_dir: Path) -> None:  # Полная очистка и пересоздание служебной директории
    try:
        if source_dir.exists():  # Если директория существует
            shutil.rmtree(source_dir)  # Удаляем её рекурсивно
            logging.info(f"Папка {source_dir} очищена")  # Сообщаем об очистке
        create_output_structure()  # Пересоздаём стандартную структуру папок
        logging.info(f"Папка {source_dir} пересоздана")  # Сообщаем о пересоздании
    except Exception as e:
        logging.error(f"Ошибка при очистке {source_dir}: {e}")  # Логируем ошибку

def clear_itog_subdirs(input_dir: Path, reports_dir: Path, upd_dir: Path) -> None:  # Очистка подпапок в каталоге ИТОГ
    logger = logging.getLogger()  # Текущий логгер
    for handler in logger.handlers[:]:  # Закрываем и снимаем обработчики (важно на Windows)
        handler.close()  # Закрыть обработчик
        logger.removeHandler(handler)  # Удалить из логгера
    for dir_path in [input_dir, reports_dir, upd_dir]:  # Перебираем целевые папки
        try:
            if dir_path.exists():  # Если папка существует
                for item in dir_path.iterdir():  # Перебираем содержимое
                    if item.is_file():  # Это файл
                        item.unlink()  # Удаляем файл
                    elif item.is_dir():  # Это папка
                        shutil.rmtree(item)  # Удаляем папку рекурсивно
                logging.info(f"Содержимое папки {dir_path} очищено")  # Сообщаем об очистке
        except Exception as e:
            logging.error(f"Ошибка при очистке {dir_path}: {e}")  # Логируем ошибку

def save_to_xlsx(codes_dict: dict, input_dir: Path):  # Сохранение коротких кодов в XLSX (для ввода в оборот)
    for pdf_name, codes in codes_dict.items():  # Перебор PDF и их списков кодов
        df = pd.DataFrame(codes)  # Создание DataFrame из списка
        xlsx_path = input_dir / f"{pdf_name}.xlsx"  # Путь к выходному файлу XLSX
        df.to_excel(xlsx_path, index=False, header=False)  # Сохранение без индексов и заголовков

def save_to_csv(extracted_codes: dict, reports_dir: Path):  # Сохранение распознанных кодов в CSV (отчёт о нанесении)
    for pdf_name, codes in extracted_codes.items():  # Перебор PDF и соответствующих кодов
        df = pd.DataFrame(codes)  # Преобразуем список в DataFrame
        csv_path = reports_dir / f"{pdf_name}.csv"  # Путь к выходному CSV
        df.to_csv(csv_path, index=False, header=False, encoding="utf-8")  # Сохраняем CSV

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

    choice = input("Что хотите получить на выходе? (1) Файлы для Ввода в оборот, (2) Файлы для отчета о нанесении, (3) Шаблон для загрузки УПД, (4) Все сразу (через пробел, например: 1 3): ")
    choices = [int(x) for x in choice.split() if x.isdigit()]
    if not choices:
        logging.error("Неверный ввод. Завершение работы")
        return

    if 4 in choices:
        choices = [1, 2, 3]
        logging.info("Выбран вариант 4: выполнение всех действий")

    logging.info("Распознавание DataMatrix-кодов...")
    try:
        extracted_codes_by_pdf = extract_datamatrix_from_image(data_matrix_dir=data_matrix_dir, reports_dir=reports_dir)
        if not extracted_codes_by_pdf:
            logging.error("Не удалось извлечь DataMatrix-коды. Завершение работы")
            return
        #logging.info(f"Извлечено кодов: {sum(len(codes) for codes in extracted_codes_by_pdf.values())}")
    except Exception as e:
        logging.error(f"Ошибка при извлечении кодов: {e}. Завершение работы")
        return

    short_codes_dict = {}  # Для Ввод в оборот
    formatted_codes_dict = {}  # Для Для УПД
    code_types = {}
    if 1 in choices or 3 in choices:
        logging.info("Форматирование КИЗ-кодов...")
        try:
            short_codes_dict, formatted_codes_dict, code_types = format_kiz_code(extracted_codes_by_pdf=extracted_codes_by_pdf, include_short_codes=True)
            if not short_codes_dict:
                logging.error("Форматирование не вернуло данных. Завершение работы")
                return
        except Exception as e:
            logging.error(f"Ошибка при форматировании кодов: {e}. Завершение работы")
            return

    if 1 in choices:
        save_to_xlsx(short_codes_dict, input_dir)
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
            generate_final_csv(formatted_codes=formatted_codes_dict, product_data=product_data, upd_dir=upd_dir, output_path=output_csv_path)
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
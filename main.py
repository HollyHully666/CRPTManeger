from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import logging  # Импортируем модуль logging для настройки логирования
import logging.handlers  # Импортируем модуль для работы с ротацией логов
from datetime import datetime  # Импортируем datetime для формирования имени лог-файла
import shutil  # Импортируем модуль shutil для операций с файлами и папками
import tkinter as tk  # Импортируем tkinter для создания графического интерфейса
from tkinter import filedialog  # Импортируем filedialog для выбора файлов
from typing import List  # Импортируем тип List для аннотаций типов

from Modules.createOutputStructure import create_output_structure  # Импортируем функцию create_output_structure для создания структуры папок
from Modules.pdf_to_png import convert_pdf_to_images  # Импортируем функцию convert_pdf_to_images для конвертации PDF в PNG
from Modules.decode_datamatrix import extract_datamatrix_from_image  # Импортируем функцию extract_datamatrix_from_image для извлечения кодов
from Modules.format_kiz_code import format_kiz_code  # Импортируем функцию format_kiz_code для форматирования кодов
from Modules.get_product_data import get_product_data  # Импортируем функцию get_product_data для получения данных о товарах
from Modules.generate_final_csv import generate_final_csv  # Импортируем функцию generate_final_csv для создания CSV

def setup_logging(log_dir: Path) -> None:  # Изменяем параметр на корневую папку
    log_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку для логов, включая родительские, если их нет
    log_file = log_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"  # Формируем имя лог-файла с текущей датой и временем
    logger = logging.getLogger()  # Получаем объект логгера
    if not logger.handlers:  # Проверяем, есть ли обработчики у логгера
        logger.setLevel(logging.INFO)  # Устанавливаем уровень логирования на INFO
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Определяем формат логов
        console_handler = logging.StreamHandler()  # Создаём обработчик для вывода в консоль
        console_handler.setFormatter(log_format)  # Устанавливаем формат для консольного обработчика
        logger.addHandler(console_handler)  # Добавляем консольный обработчик к логгеру
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)  # Создаём обработчик для файла с ротацией (10MB, 5 резервных копий)
        file_handler.setFormatter(log_format)  # Устанавливаем формат для файлового обработчика
        logger.addHandler(file_handler)  # Добавляем файловый обработчик к логгеру

def select_pdf_files() -> List[Path]:  # Определяем функцию select_pdf_files, возвращающую список путей
    root = tk.Tk()  # Создаём корневое окно tkinter
    root.withdraw()  # Скрываем основное окно
    file_paths = filedialog.askopenfilenames(  # Открываем диалог выбора файлов
        title="Выберите PDF-файлы",  # Устанавливаем заголовок диалога
        filetypes=[("PDF files", "*.pdf")]  # Ограничиваем выбор только PDF-файлами
    )  # Закрывающая скобка вызова askopenfilenames
    root.destroy()  # Уничтожаем окно после выбора
    return [Path(p) for p in file_paths]  # Преобразуем выбранные пути в объекты Path и возвращаем список

def copy_pdf_to_uploaded_dir(pdf_files: List[Path], uploaded_pdf_dir: Path) -> None:  # Определяем функцию copy_pdf_to_uploaded_dir, принимающую список путей и путь к папке
    uploaded_pdf_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку uploaded_pdf_dir, включая родительские, если их нет
    for item in uploaded_pdf_dir.iterdir():  # Цикл по всем элементам в папке uploaded_pdf_dir
        if item.is_file():  # Проверяем, является ли элемент файлом
            item.unlink()  # Если файл, удаляем его
        elif item.is_dir():  # Проверяем, является ли элемент папкой
            shutil.rmtree(item)  # Если папка, удаляем её со всем содержимым
    for pdf_file in pdf_files:  # Цикл по всем выбранным PDF-файлам
        try:  # Начинаем блок try для обработки исключений
            dest_path = uploaded_pdf_dir / pdf_file.name  # Формируем путь назначения для копирования
            shutil.copy(pdf_file, dest_path)  # Копируем файл в папку uploaded_pdf_dir
        except Exception as e:  # Ловим любые исключения при копировании
            logging.error(f"Ошибка при копировании {pdf_file}: {e}")  # Логируем ошибку

def clear_source_dir(source_dir: Path) -> None:  # Определяем функцию clear_source_dir, принимающую путь к папке и возвращающую None
    try:  # Начинаем блок try для обработки исключений
        if source_dir.exists():  # Проверяем, существует ли папка source_dir
            shutil.rmtree(source_dir)  # Если существует, удаляем её со всем содержимым
            logging.info(f"Папка {source_dir} очищена")  # Логируем успешную очистку
        create_output_structure()  # Пересоздаём структуру папок
        logging.info(f"Папка {source_dir} пересоздана")  # Логируем успешное пересоздание
    except Exception as e:  # Ловим любые исключения при очистке
        logging.error(f"Ошибка при очистке {source_dir}: {e}")  # Логируем ошибку

def clear_itog_subdirs(input_dir: Path, reports_dir: Path, upd_dir: Path) -> None:  # Определяем функцию clear_itog_subdirs, принимающую пути к папкам и возвращающую None
    # Закрываем все обработчики логирования перед очисткой
    logger = logging.getLogger()
    for handler in logger.handlers[:]:  # Копируем список обработчиков, чтобы избежать ошибки изменения во время итерации
        handler.close()  # Закрываем обработчик
        logger.removeHandler(handler)  # Удаляем обработчик из логгера

    for dir_path in [input_dir, reports_dir, upd_dir]:  # Цикл по списку путей к подпапкам ИТОГ
        try:  # Начинаем блок try для обработки исключений
            if dir_path.exists():  # Проверяем, существует ли папка
                for item in dir_path.iterdir():  # Цикл по всем элементам в папке
                    if item.is_file():  # Проверяем, является ли элемент файлом
                        item.unlink()  # Если файл, удаляем его
                    elif item.is_dir():  # Проверяем, является ли элемент папкой
                        shutil.rmtree(item)  # Если папка, удаляем её со всем содержимым
                logging.info(f"Содержимое папки {dir_path} очищено")  # Логируем успешную очистку
        except Exception as e:  # Ловим любые исключения при очистке
            logging.error(f"Ошибка при очистке {dir_path}: {e}")  # Логируем ошибку

def main():
    try:  # Начинаем блок try для обработки исключений на уровне создания структуры
        paths = create_output_structure()  # Создаём структуру папок и сохраняем словарь с путями
        uploaded_pdf_dir = paths["uploaded_pdf"]  # Извлекаем путь к папке ЗагруженныеPDF
        data_matrix_dir = paths["data_matrix"]  # Извлекаем путь к папке DATA MATRIX
        reports_dir = paths["reports"]  # Извлекаем путь к папке Отчеты о нанесении
        input_dir = paths["input_folder"]  # Извлекаем путь к папке Ввод в оборот
        upd_dir = paths["upd_folder"]  # Извлекаем путь к папке Для УПД
        source_dir = uploaded_pdf_dir.parent  # Устанавливаем путь к папке source как родительскую для uploaded_pdf_dir
        setup_logging(source_dir)  # Настраиваем логирование в корневой папке (source_dir)
        clear_itog_subdirs(input_dir, reports_dir, upd_dir)  # Очищаем содержимое подпапок ИТОГ
    except Exception as e:  # Ловим любые исключения при создании структуры
        logging.error(f"Не удалось создать структуру папок: {e}. Выход из программы")  # Логируем ошибку
        return  # Выходим из функции

    # Выбор PDF-файлов пользователем
    pdf_files = select_pdf_files()  # Запрашиваем у пользователя выбор PDF-файлов
    if not pdf_files:  # Проверяем, выбраны ли файлы
        logging.error("Не выбрано ни одного PDF-файла. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    # Копирование файлов в ЗагруженныеPDF
    copy_pdf_to_uploaded_dir(pdf_files, uploaded_pdf_dir)  # Копируем выбранные PDF-файлы в папку uploaded_pdf_dir

    POPPLER_BIN_PATH = r"C:\Tools\poppler\Library\bin"  # Устанавливаем путь к Poppler

    logging.info("Конвертация PDF в PNG...")  # Логируем начало конвертации
    try:  # Начинаем блок try для обработки исключений при конвертации
        processed_pdfs_info = convert_pdf_to_images(  # Вызываем функцию конвертации PDF в PNG
            uploaded_pdf_dir=uploaded_pdf_dir,  # Передаём путь к папке с PDF
            data_matrix_dir=data_matrix_dir,  # Передаём путь к папке для PNG
            poppler_path=POPPLER_BIN_PATH  # Передаём путь к Poppler
        )  # Закрывающая скобка вызова convert_pdf_to_images
        if not processed_pdfs_info:  # Проверяем, есть ли обработанные PDF
            logging.error("Не удалось конвертировать PDF-файлы. Завершение работы")  # Логируем ошибку
            return  # Выходим из функции
        logging.info(f"Конвертировано PDF: {len(processed_pdfs_info)} файлов")  # Логируем успешную конвертацию
    except Exception as e:  # Ловим любые исключения при конвертации
        logging.error(f"Ошибка при конвертации PDF: {e}. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    logging.info("Распознавание DataMatrix-кодов...")  # Логируем начало распознавания
    try:  # Начинаем блок try для обработки исключений при извлечении кодов
        extracted_codes_by_pdf = extract_datamatrix_from_image(  # Вызываем функцию извлечения DataMatrix-кодов
            data_matrix_dir=data_matrix_dir,  # Передаём путь к папке с PNG
            reports_dir=reports_dir  # Передаём путь к папке для отчётов
        )  # Закрывающая скобка вызова extract_datamatrix_from_image
        if not extracted_codes_by_pdf:  # Проверяем, есть ли извлечённые коды
            logging.error("Не удалось извлечь DataMatrix-коды. Завершение работы")  # Логируем ошибку
            return  # Выходим из функции
        logging.info(f"Извлечено кодов: {sum(len(codes) for codes in extracted_codes_by_pdf.values())}")  # Логируем общее количество извлечённых кодов
    except Exception as e:  # Ловим любые исключения при извлечении
        logging.error(f"Ошибка при извлечении кодов: {e}. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    logging.info("Форматирование КИЗ-кодов...")  # Логируем начало форматирования
    try:  # Начинаем блок try для обработки исключений при форматировании
        # Проверяем наличие файлов в "Отчеты о нанесении" перед форматированием
        report_files = list(reports_dir.glob("*.txt"))  # Ищем все .txt файлы в reports_dir
        if not report_files:  # Проверяем, есть ли файлы
            logging.warning("Нет файлов для форматирования в 'Отчеты о нанесении'. Пропускаем шаг.")
            formatted_codes = {}
            code_types = {}
        else:
            formatted_codes, code_types = format_kiz_code(  # Вызываем функцию форматирования кодов
                reports_dir=reports_dir,  # Передаём путь к папке с отчётами
                input_dir=input_dir,  # Передаём путь к папке для обрезанных кодов
                upd_dir=upd_dir,  # Передаём путь к папке для отформатированных кодов
                include_short_codes=True  # Указываем, что короткие коды включаются
            )  # Получаем отформатированные коды и типы кодов
            if not formatted_codes:  # Проверяем, есть ли отформатированные коды
                logging.warning("Форматирование не вернуло данных. Возможна ошибка в обработке.")
        logging.info(f"Обработано файлов: {len(formatted_codes)}")  # Логируем количество обработанных файлов
    except Exception as e:  # Ловим любые исключения при форматировании
        logging.error(f"Ошибка при форматировании кодов: {e}. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    logging.info("Запрос данных о товарах...")  # Логируем начало запроса данных
    try:  # Начинаем блок try для обработки исключений при запросе данных
        product_data = get_product_data(  # Вызываем функцию получения данных о товарах
            uploaded_pdf_dir=uploaded_pdf_dir,  # Передаём путь к папке с PDF
            reports_dir=reports_dir,  # Передаём путь к папке для отчётов
            extracted_codes_by_pdf=extracted_codes_by_pdf,  # Передаём словарь с извлечёнными кодами
            code_types=code_types  # Передаём словарь с типами кодов
        )  # Закрывающая скобка вызова get_product_data
        if not product_data:  # Проверяем, есть ли данные о товарах
            logging.error("Не получены данные о товарах. Завершение работы")  # Логируем ошибку
            return  # Выходим из функции
    except Exception as e:  # Ловим любые исключения при запросе данных
        logging.error(f"Ошибка при запросе данных о товарах: {e}. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    logging.info("Генерация итогового CSV...")  # Логируем начало генерации CSV
    try:  # Начинаем блок try для обработки исключений при генерации CSV
        output_csv_path = upd_dir / "final_upd.csv"  # Формируем путь к итоговому CSV-файлу
        generate_final_csv(  # Вызываем функцию генерации CSV
            reports_dir=reports_dir,  # Передаём путь к папке с отчётами
            upd_dir=upd_dir,  # Передаём путь к папке с отформатированными кодами
            output_path=output_csv_path  # Передаём путь для сохранения CSV
        )  # Закрывающая скобка вызова generate_final_csv
    except Exception as e:  # Ловим любые исключения при генерации
        logging.error(f"Ошибка при создании CSV: {e}. Завершение работы")  # Логируем ошибку
        return  # Выходим из функции

    logging.info("Программа успешно завершена")  # Логируем успешное завершение
    logging.info(f"Итоговый CSV: {output_csv_path}")  # Логируем путь к итоговому CSV

    # Очистка папки source
    clear_source_dir(source_dir)  # Очищаем папку source

if __name__ == "__main__":  # Проверяем, запущен ли файл как основной
    try:  # Начинаем блок try для обработки исключений на уровне программы
        main()  # Вызываем основную функцию main
    except KeyboardInterrupt:  # Ловим прерывание пользователем (Ctrl+C)
        logging.warning("Программа прервана пользователем")  # Логируем прерывание
    except Exception as e:  # Ловим любые другие исключения
        logging.error(f"Критическая ошибка: {e}")  # Логируем критическую ошибку
    finally:  # Выполняется в любом случае (при успехе, ошибке или прерывании)
        # Закрываем логгеры перед финальной очисткой
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        paths = create_output_structure()  # Пересоздаём структуру папок
        source_dir = paths["uploaded_pdf"].parent  # Получаем путь к папке source
        clear_source_dir(source_dir)  # Очищаем папку source
from pathlib import Path
import logging
import re

if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов.
    Args:
        filename (str): Исходное имя файла.
    Returns:
        str: Очищенное имя файла.
    """
    return re.sub(r'[^\w\-]', '_', filename)

def apply_format(code: str) -> str:
    """
    Применяет форматирование к коду идентификации (КИ) согласно требованиям Честного знака:
    - Если в КИ есть запятая (,), весь КИ оборачивается в двойные кавычки (").
    - Если в КИ есть запятая (,) и кавычки ("), весь КИ оборачивается в двойные кавычки ("), 
      а каждая двойная кавычка внутри текста экранируется второй кавычкой (").
    - В остальных случаях возвращает код без изменений.
    Args:
        code (str): Исходный DataMatrix-код.
    Returns:
        str: Отформатированный код.
    """
    if ',' in code:
        # Если есть запятая, оборачиваем в двойные кавычки и экранируем внутренние кавычки
        return f'"{code.replace('"', '""')}"'
    return code

def format_kiz_code(reports_dir: Path, input_dir: Path, upd_dir: Path, include_short_codes: bool = False) -> dict[str, list[str]]:
    """
    Обрабатывает DataMatrix-коды из файлов <pdf_name>.txt в reports_dir:
    1. Обрезает коды до 31 символа и сохраняет в input_dir/<pdf_name>.txt.
    2. Форматирует коды (apply_format) и сохраняет в upd_dir/<pdf_name>.txt.
    Args:
        reports_dir (Path): Путь к директории "ИТОГ/Отчеты о нанесении" с файлами <pdf_name>.txt.
        input_dir (Path): Путь к директории "ИТОГ/Ввод в оборот" для обрезанных кодов.
        upd_dir (Path): Путь к директории "ИТОГ/Для УПД" для отформатированных кодов.
        include_short_codes (bool): Если True, включает коды короче 31 символа.
    Returns:
        dict[str, list[str]]: Словарь, где ключ - имя PDF, а значение - список отформатированных кодов.
    """
    formatted_codes = {}
    failed_files = []

    #logging.info(f"Начинаю обработку кодов из: {reports_dir}")

    # Ищем файлы <pdf_name>.txt
    found_files = list(reports_dir.glob("*.txt"))
    if not found_files:
        #logging.warning(f"Не найдено файлов '*.txt' в {reports_dir}")
        return formatted_codes

    # Создаём директории
    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        upd_dir.mkdir(parents=True, exist_ok=True)
        #logging.info(f"Папки созданы или существуют: {input_dir}, {upd_dir}")
    except OSError as e:
        #logging.error(f"Ошибка при создании папок {input_dir} или {upd_dir}: {e}")
        return formatted_codes

    for txt_file in found_files:
        pdf_name = sanitize_filename(txt_file.stem)  # Убираем .txt
        #logging.info(f"Обрабатываю файл: {txt_file.name} (PDF: {pdf_name})")
        short_codes = []
        current_formatted_codes = []

        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    #logging.warning(f"Файл '{txt_file}' пуст. Пропускаю.")
                    continue

                for line_num, line in enumerate(lines, 1):
                    code = line.strip()
                    if not code:
                        #logging.debug(f"Пропущена пустая строка {line_num} в {txt_file.name}")
                        continue

                    # Обрезаем до 31 символа
                    if len(code) >= 31:
                        short_code = code[:31]
                    elif include_short_codes:
                        short_code = code
                        #logging.warning(
                           # f"Код короче 31 символа в {txt_file.name}, строка {line_num}: '{code}'"
                       # )
                    else:
                        #logging.warning(
                            #f"Пропущен код (<31 символ) в {txt_file.name}, строка {line_num}: '{code}'"
                        #)
                        continue

                    short_codes.append(short_code)
                    formatted_code = apply_format(short_code)
                    current_formatted_codes.append(formatted_code)

            if not short_codes:
                #logging.warning(f"Нет подходящих кодов в {txt_file}. Файлы не созданы.")
                continue

            # Сохраняем обрезанные коды
            short_path = input_dir / f"{pdf_name}.txt"
            try:
                with open(short_path, "w", encoding="utf-8") as f:
                    for code in short_codes:
                        f.write(code + "\n")
                #logging.info(f"Сохранен файл обрезанных кодов: {short_path} ({len(short_codes)} кодов)")
            except OSError as e:
                #logging.error(f"Ошибка при записи {short_path}: {e}")
                failed_files.append(txt_file.name)
                continue

            # Сохраняем отформатированные коды
            formatted_path = upd_dir / f"{pdf_name}.txt"
            try:
                with open(formatted_path, "w", encoding="utf-8") as f:
                    for code in current_formatted_codes:
                        f.write(code + "\n")
                #logging.info(f"Сохранен файл отформатированных кодов: {formatted_path} ({len(current_formatted_codes)} кодов)")
                formatted_codes[pdf_name] = current_formatted_codes
            except OSError as e:
                #logging.error(f"Ошибка при записи {formatted_path}: {e}")
                failed_files.append(txt_file.name)
                continue

        except FileNotFoundError:
            #logging.error(f"Файл не найден: {txt_file}")
            failed_files.append(txt_file.name)
            continue
        except OSError as e:
            #logging.error(f"Ошибка при чтении {txt_file}: {e}")
            failed_files.append(txt_file.name)
            continue
        except Exception as e:
            #logging.error(f"Непредвиденная ошибка при обработке {txt_file}: {e}")
            failed_files.append(txt_file.name)
            continue

    if failed_files:
        logging.warning(f"Не удалось обработать файлы: {', '.join(failed_files)}")

    return formatted_codes
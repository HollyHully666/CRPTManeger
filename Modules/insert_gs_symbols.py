from pathlib import Path
import logging
import re

# Условная настройка логирования
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

def insert_gs_symbols(reports_dir: Path) -> dict[str, list[str]]:
    """
    Вставляет символ-разделитель GS (ASCII 29) в DataMatrix-коды.

    GS вставляется после 31-го символа и после следующих 8 символов (39-й символ исходной строки).
    Обрабатывает файлы 'gs_codes.txt' в подпапках директории reports_dir и перезаписывает их.

    Args:
        reports_dir (Path): Путь к директории "Отчеты о нанесении" с подпапками и файлами gs_codes.txt.

    Returns:
        dict[str, list[str]]: Словарь, где ключ - имя подпапки (PDF), а значение - список обновленных кодов.

    Raises:
        OSError: Если не удалось прочитать или записать файл gs_codes.txt.
    """
    gs_char = chr(29)  # Символ-разделитель группы (Group Separator)
    updated_codes = {}
    failed_files = []

    logging.info(f"Начинаю вставку GS-символов в коды в: {reports_dir}")

    # Ищем файлы gs_codes.txt в подпапках
    found_files = list(reports_dir.glob("*/gs_codes.txt"))

    if not found_files:
        logging.warning(f"Не найдено файлов 'gs_codes.txt' в подпапках {reports_dir}.")
        return updated_codes

    for txt_file in found_files:
        pdf_name = sanitize_filename(txt_file.parent.name)
        logging.info(f"Обрабатываю файл: {txt_file.name} (папка: {pdf_name})")
        updated_lines = []

        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    logging.warning(f"Файл '{txt_file}' пуст. Пропускаю.")
                    continue

                for line_num, line in enumerate(lines, 1):
                    code = line.strip()
                    if not code:
                        logging.debug(f"Пропущена пустая строка {line_num} в {txt_file.name}")
                        continue

                    # Вставка GS после 31-го символа
                    if len(code) >= 31:
                        new_code = code[:31] + gs_char + code[31:]
                    else:
                        logging.warning(
                            f"Код слишком короткий (<31 символ) в {txt_file.name}, строка {line_num}: '{code}'"
                        )
                        updated_lines.append(code)
                        continue

                    # Вставка GS после следующих 8 символов (39-й символ исходного кода)
                    if len(code) >= 39:
                        new_code = new_code[:40] + gs_char + new_code[40:]  # 31 + 8 + 1 (первый GS) = 40
                    else:
                        logging.warning(
                            f"Код слишком короткий (<39 символов) для второго GS в {txt_file.name}, строка {line_num}: '{code}'"
                        )

                    updated_lines.append(new_code)

            # Сохраняем обновленные коды
            if updated_lines:
                try:
                    with open(txt_file, "w", encoding="utf-8") as f:
                        for line in updated_lines:
                            f.write(line + "\n")
                    logging.info(f"✅ Обновлен файл: {txt_file} ({len(updated_lines)} кодов)")
                    updated_codes[pdf_name] = updated_lines
                except OSError as e:
                    logging.error(f"Ошибка при записи в {txt_file}: {e}")
                    failed_files.append(txt_file.name)
            else:
                logging.warning(f"Нет кодов для записи в {txt_file}. Файл не перезаписан.")

        except FileNotFoundError:
            logging.error(f"Файл не найден: {txt_file}")
            failed_files.append(txt_file.name)
            continue
        except OSError as e:
            logging.error(f"Ошибка при чтении {txt_file}: {e}")
            failed_files.append(txt_file.name)
            continue
        except Exception as e:
            logging.error(f"Непредвиденная ошибка при обработке {txt_file}: {e}")
            failed_files.append(txt_file.name)
            continue

    if failed_files:
        logging.warning(f"Не удалось обработать файлы: {', '.join(failed_files)}")

    return updated_codes

if __name__ == "__main__":
    from createOutputStructure import create_output_structure

    # Получаем пути из createOutputStructure
    paths = create_output_structure()
    REPORTS_DIR = paths.get("reports", Path("./Отчеты о нанесении"))

    # Создаем тестовые данные
    TEST_REPORTS_DIR = REPORTS_DIR
    TEST_REPORTS_DIR.mkdir(exist_ok=True)
    (TEST_REPORTS_DIR / "pdf_name_A").mkdir(exist_ok=True)
    (TEST_REPORTS_DIR / "pdf_name_B").mkdir(exist_ok=True)

    # Создаем тестовые файлы gs_codes.txt
    with open(TEST_REPORTS_DIR / "pdf_name_A" / "gs_codes.txt", "w", encoding="utf-8") as f:
        f.write("0123456789012345678901234567890ABCDEFGH1234567890\n")  # Длина 49
        f.write("SHORT_CODE_LESS_THAN_31_CHARS\n")  # Длина < 31
        f.write("CODE_LENGTH_BETWEEN_31_AND_39_CHARS_35_LONG\n")  # Длина 35

    with open(TEST_REPORTS_DIR / "pdf_name_B" / "gs_codes.txt", "w", encoding="utf-8") as f:
        f.write("ANOTHER_CODE_012345678901234567890ABCDEFGH1234567890\n")  # Длина 49

    logging.info("Запуск функции insert_gs_symbols...")
    try:
        updated_codes_info = insert_gs_symbols(TEST_REPORTS_DIR)

        logging.info("\n--- Результаты обработки ---")
        gs_char_display = "[GS]"
        for pdf_name, codes in updated_codes_info.items():
            logging.info(f"PDF: {pdf_name}, Обработано кодов: {len(codes)}")
            for code in codes:
                logging.info(f"  - {code.replace(chr(29), gs_char_display)}")
    except Exception as e:
        logging.error(f"Ошибка при выполнении: {e}")
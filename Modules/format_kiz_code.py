from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import re  # Импортируем модуль re для работы с регулярными выражениями

def sanitize_filename(filename: str) -> str:  # Определяем функцию sanitize_filename, принимающую строку и возвращающую очищенную строку
    return re.sub(r'[^\w\-]', '_', filename)  # Заменяем все символы, кроме букв, цифр и дефисов, на подчеркивание и возвращаем результат

def apply_format(code: str) -> str:  # Определяем функцию apply_format, принимающую строку и возвращающую отформатированную строку
    if ',' in code:  # Проверяем, есть ли в строке запятая
        return f'"{code.replace('"', '""')}"'  # Если есть запятая, оборачиваем строку в кавычки и экранируем внутренние кавычки, возвращаем результат
    return code  # Если запятой нет, возвращаем строку без изменений

def format_kiz_code(reports_dir: Path, input_dir: Path, upd_dir: Path, include_short_codes: bool = False) -> dict[str, list[str]]:  # Определяем функцию format_kiz_code, принимающую пути и булевый флаг, возвращающую словарь
    formatted_codes = {}  # Инициализируем пустой словарь для хранения отформатированных кодов
    failed_files = []  # Инициализируем пустой список для хранения имён файлов, которые не удалось обработать

    found_files = list(reports_dir.glob("*.txt"))  # Ищем все .txt файлы в reports_dir и преобразуем в список
    if not found_files:  # Проверяем, есть ли .txt файлы в списке
        return formatted_codes  # Если файлов нет, возвращаем пустой словарь

    try:  # Начинаем блок try для обработки исключений при создании папок
        input_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку input_dir, включая родительские, если их нет
        upd_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку upd_dir, включая родительские, если их нет
    except OSError as e:  # Ловим ошибки ввода-вывода при создании папок
        return formatted_codes  # В случае ошибки возвращаем пустой словарь

    for txt_file in found_files:  # Цикл по всем найденным .txt файлам
        pdf_name = sanitize_filename(txt_file.stem)  # Извлекаем имя файла без расширения и очищаем его
        short_codes = []  # Инициализируем пустой список для хранения обрезанных кодов
        current_formatted_codes = []  # Инициализируем пустой список для хранения отформатированных кодов

        try:  # Начинаем блок try для обработки текущего файла
            with open(txt_file, "r", encoding="utf-8") as f:  # Открываем файл для чтения в кодировке UTF-8
                lines = f.readlines()  # Читаем все строки файла в список
                if not lines:  # Проверяем, есть ли строки в файле
                    continue  # Если файл пуст, пропускаем его

                for line_num, line in enumerate(lines, 1):  # Цикл по строкам файла с нумерацией, начиная с 1
                    code = line.strip()  # Удаляем пробелы и переносы строки из текущей строки
                    if not code:  # Проверяем, пустая ли строка после очистки
                        continue  # Если строка пустая, пропускаем её

                    if len(code) >= 31:  # Проверяем, больше или равна ли длина кода 31 символу
                        short_code = code[:31]  # Если код длинный, обрезаем его до 31 символа
                    elif include_short_codes:  # Проверяем, включать ли короткие коды (флаг include_short_codes)
                        short_code = code  # Если короткие коды включены, оставляем код как есть
                    else:  # Если короткие коды не включены
                        continue  # Пропускаем код, если он короче 31 символа

                    short_codes.append(short_code)  # Добавляем обрезанный код в список short_codes
                    formatted_code = apply_format(short_code)  # Форматируем обрезанный код с помощью apply_format
                    current_formatted_codes.append(formatted_code)  # Добавляем отформатированный код в список current_formatted_codes

            if not short_codes:  # Проверяем, есть ли обрезанные коды
                continue  # Если кодов нет, пропускаем текущий файл

            short_path = input_dir / f"{pdf_name}.txt"  # Формируем путь для файла с обрезанными кодами
            try:  # Начинаем блок try для записи обрезанных кодов
                with open(short_path, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
                    for code in short_codes:  # Цикл по всем обрезанным кодам
                        f.write(code + "\n")  # Записываем код в файл с переносом строки
            except OSError as e:  # Ловим ошибки ввода-вывода при записи файла
                failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
                continue  # Пропускаем текущий файл

            formatted_path = upd_dir / f"{pdf_name}.txt"  # Формируем путь для файла с отформатированными кодами
            try:  # Начинаем блок try для записи отформатированных кодов
                with open(formatted_path, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
                    for code in current_formatted_codes:  # Цикл по всем отформатированным кодам
                        f.write(code + "\n")  # Записываем код в файл с переносом строки
                formatted_codes[pdf_name] = current_formatted_codes  # Добавляем отформатированные коды в словарь formatted_codes
            except OSError as e:  # Ловим ошибки ввода-вывода при записи файла
                failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
                continue  # Пропускаем текущий файл

        except FileNotFoundError:  # Ловим ошибку, если файл не найден
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл
        except OSError as e:  # Ловим ошибки ввода-вывода при чтении файла
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл
        except Exception as e:  # Ловим любые другие исключения
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл

    return formatted_codes  # Возвращаем словарь с отформатированными кодами
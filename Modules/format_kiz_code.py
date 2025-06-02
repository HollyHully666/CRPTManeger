from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import re  # Импортируем модуль re для работы с регулярными выражениями

def sanitize_filename(filename: str) -> str:  # Определяем функцию sanitize_filename, принимающую строку и возвращающую очищенную строку
    return re.sub(r'[^\w\-]', '_', filename)  # Заменяем все символы, кроме букв, цифр и дефисов, на подчеркивание и возвращаем результат

def apply_format(code: str) -> str:  # Определяем функцию apply_format, принимающую строку и возвращающую отформатированную строку
    if ',' in code:  # Проверяем, есть ли в строке запятая
        return f'"{code.replace('"', '""')}"'  # Если есть запятая, оборачиваем строку в кавычки и экранируем внутренние кавычки, возвращаем результат
    return code  # Если запятой нет, возвращаем строку без изменений

def identify_code_type(code: str) -> str:  # Функция для определения типа кода
    # КИЗ стандартный: 01[14 цифр]21[13 букв/цифр/символов], длина 31
    if len(code) == 31 and re.match(r'^01\d{14}21[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'"<>,.?/|]{13}$', code):
        return "КИЗ"
    # КИЗ укороченный: 01[14 цифр]21[6 букв/цифр/символов], длина 24
    elif len(code) == 24 and re.match(r'^01\d{14}21[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'"<>,.?/|]{6}$', code):
        return "КИЗ"
    # НомУпак: 02[14 цифр]37[1-4 цифры], длина 19-22
    elif 19 <= len(code) <= 22 and re.match(r'^02\d{14}37\d{1,4}$', code):
        return "НомУпак"
    # ИдентТрансУпак: 00[1 цифра][7-9 цифр][6-8 цифр][1 цифра], длина 18
    elif len(code) == 18 and re.match(r'^00\d{1}\d{7,9}\d{6,8}\d{1}$', code):
        prefix = code[3:12] if len(code[3:12]) == 9 else code[3:10]  # Префикс 7-9 цифр
        serial = code[12:-1] if len(prefix) == 9 else code[10:-1]  # Серийный номер 6-8 цифр
        if (len(prefix) == 9 and len(serial) == 6) or (len(prefix) == 7 and len(serial) == 8):
            return "ИдентТрансУпак"
    return "Неизвестный"  # Если код не соответствует ни одному типу

def format_kiz_code(reports_dir: Path, input_dir: Path, upd_dir: Path, include_short_codes: bool = False) -> tuple[dict[str, list[str]], dict[str, str]]:  # Изменяем возвращаемый тип
    formatted_codes = {}  # Инициализируем пустой словарь для хранения отформатированных кодов
    code_types = {}  # Новый словарь для хранения типов кодов по файлам
    failed_files = []  # Инициализируем пустой список для хранения имён файлов, которые не удалось обработать

    found_files = list(reports_dir.glob("*.txt"))  # Ищем все .txt файлы в reports_dir и преобразуем в список
    if not found_files:  # Проверяем, есть ли .txt файлы в списке
        print(f"Нет файлов в {reports_dir}")  # Отладка: выводим предупреждение
        return formatted_codes, code_types  # Возвращаем пустые словари

    try:  # Начинаем блок try для обработки исключений при создании папок
        input_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку input_dir, включая родительские, если их нет
        upd_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку upd_dir, включая родительские, если их нет
    except OSError as e:  # Ловим ошибки ввода-вывода при создании папок
        print(f"Ошибка создания папок: {e}")  # Отладка: выводим ошибку
        return formatted_codes, code_types  # В случае ошибки возвращаем пустые словари

    for txt_file in found_files:  # Цикл по всем найденным .txt файлам
        pdf_name = sanitize_filename(txt_file.stem)  # Извлекаем имя файла без расширения и очищаем его
        short_codes = []  # Инициализируем пустой список для хранения обрезанных кодов
        current_formatted_codes = []  # Инициализируем пустой список для хранения отформатированных кодов
        file_code_type = None  # Переменная для хранения типа кода для текущего файла

        try:  # Начинаем блок try для обработки текущего файла
            with open(txt_file, "r", encoding="utf-8") as f:  # Открываем файл для чтения в кодировке UTF-8
                lines = f.readlines()  # Читаем все строки файла в список
                if not lines:  # Проверяем, есть ли строки в файле
                    print(f"Файл {txt_file} пуст")  # Отладка: выводим предупреждение
                    continue  # Если файл пуст, пропускаем его

                for line_num, line in enumerate(lines, 1):  # Цикл по строкам файла с нумерацией, начиная с 1
                    code = line.strip()  # Удаляем пробелы и переносы строки из текущей строки
                    if not code:  # Проверяем, пустая ли строка после очистки
                        print(f"Пустая строка в {txt_file}, строка {line_num}")  # Отладка: выводим предупреждение
                        continue  # Если строка пустая, пропускаем её

                    print(f"Исходный код в {txt_file}, строка {line_num}: {repr(code)}")  # Отладка: выводим код с видимыми специальными символами
                    gs_index = code.find('\x1D')  # Ищем позицию символа GS (ASCII 29)
                    print(f"Позиция GS: {gs_index}")  # Отладка: выводим позицию GS
                    if gs_index == 24:  # Если GS на позиции 24 (длина 24, укороченный код)
                        short_code = code[:24]  # Обрезаем до 24 символов
                        print(f"Обнаружен укороченный код: {repr(short_code)}")  # Отладка: выводим обрезанный код
                    elif gs_index == 31:  # Если GS на позиции 31 (длина 31, стандартный код)
                        short_code = code[:31]  # Обрезаем до 31 символа
                        print(f"Обнаружен стандартный код: {repr(short_code)}")  # Отладка: выводим обрезанный код
                    elif include_short_codes and len(code) < 24:  # Проверяем, включать ли короткие коды (менее 24 символов)
                        short_code = code  # Если включены, оставляем код как есть
                        print(f"Короткий код (менее 24): {repr(short_code)}")  # Отладка: выводим код
                    else:  # Если код не соответствует ни одному типу
                        print(f"Код не распознан: {repr(code)}")  # Отладка: выводим нераспознанный код
                        continue  # Пропускаем код

                    # Определяем тип кода
                    current_code_type = identify_code_type(short_code)
                    print(f"Тип кода: {current_code_type}")  # Отладка: выводим тип кода
                    if file_code_type is None:  # Если тип ещё не определён
                        file_code_type = current_code_type
                    elif file_code_type != current_code_type:  # Проверяем, совпадает ли тип с предыдущими
                        print(f"Несоответствие типов кодов в {txt_file}: {file_code_type} и {current_code_type}")
                        continue  # Пропускаем, если типы не совпадают

                    short_codes.append(short_code)  # Добавляем обрезанный код в список short_codes
                    formatted_code = apply_format(short_code)  # Форматируем обрезанный код с помощью apply_format
                    current_formatted_codes.append(formatted_code)  # Добавляем отформатированный код в список current_formatted_codes

            if not short_codes:  # Проверяем, есть ли обрезанные коды
                print(f"Нет обработанных кодов в {txt_file}")  # Отладка: выводим предупреждение
                continue  # Если кодов нет, пропускаем текущий файл

            short_path = input_dir / f"{pdf_name}.txt"  # Формируем путь для файла с обрезанными кодами
            try:  # Начинаем блок try для записи обрезанных кодов
                with open(short_path, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
                    for code in short_codes:  # Цикл по всем обрезанным кодам
                        f.write(code + "\n")  # Записываем код в файл с переносом строки
            except OSError as e:  # Ловим ошибки ввода-вывода при записи файла
                print(f"Ошибка записи в {short_path}: {e}")  # Отладка: выводим ошибку
                failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
                continue  # Пропускаем текущий файл

            formatted_path = upd_dir / f"{pdf_name}.txt"  # Формируем путь для файла с отформатированными кодами
            try:  # Начинаем блок try для записи отформатированных кодов
                with open(formatted_path, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
                    for code in current_formatted_codes:  # Цикл по всем отформатированным кодам
                        f.write(code + "\n")  # Записываем код в файл с переносом строки
                formatted_codes[pdf_name] = current_formatted_codes  # Добавляем отформатированные коды в словарь formatted_codes
                if file_code_type:  # Если тип кода определён
                    code_types[pdf_name] = file_code_type  # Сохраняем тип кода для файла
            except OSError as e:  # Ловим ошибки ввода-вывода при записи файла
                print(f"Ошибка записи в {formatted_path}: {e}")  # Отладка: выводим ошибку
                failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
                continue  # Пропускаем текущий файл

        except FileNotFoundError:  # Ловим ошибку, если файл не найден
            print(f"Файл не найден: {txt_file}")  # Отладка: выводим предупреждение
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл
        except OSError as e:  # Ловим ошибки ввода-вывода при чтении файла
            print(f"Ошибка чтения {txt_file}: {e}")  # Отладка: выводим ошибку
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл
        except Exception as e:  # Ловим любые другие исключения
            print(f"Неизвестная ошибка в {txt_file}: {e}")  # Отладка: выводим ошибку
            failed_files.append(txt_file.name)  # Добавляем имя файла в список failed_files
            continue  # Пропускаем текущий файл

    return formatted_codes, code_types  # Возвращаем отформатированные коды и типы кодов
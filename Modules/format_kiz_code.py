from pathlib import Path
import re

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^\w\-]', '_', filename)

def apply_format(code: str) -> str:
    if ',' in code:
        return f'"{code.replace('"', '""')}"'
    return code

def identify_code_type(code: str) -> str:
    if len(code) == 31 and re.match(r'^01\d{14}21[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'"<>,.?/|]{13}$', code):
        return "КИЗ"
    elif len(code) == 24 and re.match(r'^01\d{14}21[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'"<>,.?/|]{6}$', code):
        return "КИЗ"
    elif 19 <= len(code) <= 22 and re.match(r'^02\d{14}37\d{1,4}$', code):
        return "НомУпак"
    elif len(code) == 18 and re.match(r'^00\d{1}\d{7,9}\d{6,8}\d{1}$', code):
        prefix = code[3:12] if len(code[3:12]) == 9 else code[3:10]
        serial = code[12:-1] if len(prefix) == 9 else code[10:-1]
        if (len(prefix) == 9 and len(serial) == 6) or (len(prefix) == 7 and len(serial) == 8):
            return "ИдентТрансУпак"
    return "Неизвестный"

def format_kiz_code(extracted_codes_by_pdf: dict[str, list[str]], input_dir: Path, upd_dir: Path, include_short_codes: bool = False, write_input: bool = True, write_upd: bool = True) -> tuple[dict[str, list[str]], dict[str, str]]:
    formatted_codes = {}
    code_types = {}
    failed_files = []

    if not extracted_codes_by_pdf:
        print("Нет извлечённых кодов для обработки")
        return formatted_codes, code_types

    try:
        if write_input:
            input_dir.mkdir(parents=True, exist_ok=True)
        if write_upd:
            upd_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Ошибка создания папок: {e}")
        return formatted_codes, code_types

    for pdf_name, codes in extracted_codes_by_pdf.items():
        pdf_name = sanitize_filename(pdf_name)
        short_codes = []
        current_formatted_codes = []
        file_code_type = None

        if not codes:
            print(f"Нет кодов для {pdf_name}")
            continue

        for line_num, code in enumerate(codes, 1):
            code = code.strip()
            if not code:
                print(f"Пустой код для {pdf_name}, строка {line_num}")
                continue

            print(f"Исходный код для {pdf_name}, строка {line_num}: {repr(code)}")
            gs_index = code.find('\x1D')
            print(f"Позиция GS: {gs_index}")
            if gs_index == 24:
                short_code = code[:24]
                print(f"Обнаружен укороченный код: {repr(short_code)}")
            elif gs_index == 31:
                short_code = code[:31]
                print(f"Обнаружен стандартный код: {repr(short_code)}")
            elif include_short_codes and len(code) < 24:
                short_code = code
                print(f"Короткий код (менее 24): {repr(short_code)}")
            else:
                print(f"Код не распознан: {repr(code)}")
                continue

            current_code_type = identify_code_type(short_code)
            print(f"Тип кода: {current_code_type}")
            if file_code_type is None:
                file_code_type = current_code_type
            elif file_code_type != current_code_type:
                print(f"Несоответствие типов кодов для {pdf_name}: {file_code_type} и {current_code_type}")
                continue

            short_codes.append(short_code)
            formatted_code = apply_format(short_code)
            current_formatted_codes.append(formatted_code)

        if not short_codes:
            print(f"Нет обработанных кодов для {pdf_name}")
            continue

        if write_input:
            short_path = input_dir / f"{pdf_name}.txt"
            try:
                with open(short_path, "w", encoding="utf-8") as f:
                    for code in short_codes:
                        f.write(code + "\n")
            except OSError as e:
                print(f"Ошибка записи в {short_path}: {e}")
                failed_files.append(pdf_name)
                continue

        if write_upd:
            formatted_path = upd_dir / f"{pdf_name}.txt"
            try:
                with open(formatted_path, "w", encoding="utf-8") as f:
                    for code in current_formatted_codes:
                        f.write(code + "\n")
            except OSError as e:
                print(f"Ошибка записи в {formatted_path}: {e}")
                failed_files.append(pdf_name)
                continue

        formatted_codes[pdf_name] = current_formatted_codes
        if file_code_type:
            code_types[pdf_name] = file_code_type

    return formatted_codes, code_types
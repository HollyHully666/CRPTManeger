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

def format_kiz_code(
    extracted_codes_by_pdf: dict[str, list[str]],
    include_short_codes: bool = False,
    verbose: bool = False,
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, str], dict]:
    """
    Возвращает (short_codes_dict, formatted_codes_dict, code_types, format_stats).
    format_stats: skipped_empty, skipped_format, skipped_type_mismatch, accepted.
    """
    short_codes_dict = {}
    formatted_codes_dict = {}
    code_types = {}
    format_stats = {"skipped_empty": 0, "skipped_format": 0, "skipped_type_mismatch": 0, "accepted": 0}

    if not extracted_codes_by_pdf:
        return short_codes_dict, formatted_codes_dict, code_types, format_stats

    for pdf_name, codes in extracted_codes_by_pdf.items():
        pdf_name = sanitize_filename(pdf_name)
        short_codes = []
        current_formatted_codes = []
        file_code_type = None

        if not codes:
            continue

        for line_num, code in enumerate(codes, 1):
            code = code.strip()
            if not code:
                format_stats["skipped_empty"] += 1
                if verbose:
                    print(f"Пустой код для {pdf_name}, строка {line_num}")
                continue

            if verbose:
                print(f"Исходный код для {pdf_name}, строка {line_num}: {repr(code)}")
            gs_index = code.find("\x1D")
            if gs_index == 24:
                short_code = code[:24]
            elif gs_index == 31:
                short_code = code[:31]
            elif include_short_codes and len(code) < 24:
                short_code = code
            else:
                format_stats["skipped_format"] += 1
                if verbose:
                    print(f"Код не распознан (формат): {pdf_name}, строка {line_num}, repr={repr(code)[:50]}")
                continue

            current_code_type = identify_code_type(short_code)
            if file_code_type is None:
                file_code_type = current_code_type
            elif file_code_type != current_code_type:
                format_stats["skipped_type_mismatch"] += 1
                if verbose:
                    print(f"Несоответствие типов для {pdf_name}: {file_code_type} и {current_code_type}")
                continue

            short_codes.append(short_code)
            current_formatted_codes.append(apply_format(short_code))
            format_stats["accepted"] += 1

        if not short_codes:
            continue

        short_codes_dict[pdf_name] = short_codes
        formatted_codes_dict[pdf_name] = current_formatted_codes
        if file_code_type:
            code_types[pdf_name] = file_code_type

    return short_codes_dict, formatted_codes_dict, code_types, format_stats
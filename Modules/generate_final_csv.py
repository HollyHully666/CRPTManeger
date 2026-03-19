from pathlib import Path

# Максимум кодов в одном файле шаблона УПД (ограничение Честного знака)
MAX_CODES_PER_FILE = 30000


def _chunk_list(lst: list, chunk_size: int):
    """Разбивает список на части не больше chunk_size элементов."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def generate_final_csv(
    formatted_codes: dict[str, list[str]],
    product_data: dict,
    upd_dir: Path,
    output_path: Path | None = None,
    max_codes_per_file: int = MAX_CODES_PER_FILE,
) -> list[Path]:
    output_path = output_path or (upd_dir / "final_upd.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stem = output_path.stem
    suffix = output_path.suffix
    parent = output_path.parent

    written_paths: list[Path] = []
    current_file_rows: list[str] = []
    current_code_count = 0
    file_index = 1
    row_index_in_file = 1

    for pdf_name, codes in formatted_codes.items():
        if not codes or pdf_name not in product_data:
            continue

        data_list = product_data.get(pdf_name, [])
        if not data_list:
            continue

        data = data_list[0] if isinstance(data_list, list) else data_list
        name, price, quantity, okei, vat, code_type = data
        vat = "без НДС" if vat == "none" else vat

        for code_chunk in _chunk_list(codes, max_codes_per_file):
            chunk_size = len(code_chunk)
            # Если добавление этого блока превысит лимит и в текущем файле уже есть строки — пишем файл и начинаем новый
            if current_code_count + chunk_size > max_codes_per_file and current_file_rows:
                part_path = parent / f"{stem}_part{file_index}{suffix}"
                _write_csv_rows(part_path, current_file_rows)
                written_paths.append(part_path)
                current_file_rows = []
                current_code_count = 0
                file_index += 1
                row_index_in_file = 1

            # Одна строка с данными товара и первым кодом, остальные — только коды
            current_file_rows.append(
                f"{row_index_in_file},{name},{price},{chunk_size},{okei},{vat},{code_type},{code_chunk[0]}"
            )
            for code in code_chunk[1:]:
                current_file_rows.append(f"{row_index_in_file},,,,,,{code_type},{code}")
            row_index_in_file += 1
            current_code_count += chunk_size

    if not current_file_rows:
        print("Нет данных для создания CSV")
        return written_paths

    # Один файл — сохраняем по переданному пути (final_upd.csv), иначе — final_upd_part1.csv, part2, ...
    if file_index == 1:
        part_path = output_path
    else:
        part_path = parent / f"{stem}_part{file_index}{suffix}"
    _write_csv_rows(part_path, current_file_rows)
    written_paths.append(part_path)
    return written_paths


def _write_csv_rows(path: Path, rows: list[str]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
    except Exception as e:
        print(f"Ошибка при записи CSV {path}: {e}")

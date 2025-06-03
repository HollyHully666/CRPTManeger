from pathlib import Path
import pandas as pd

def generate_final_csv(formatted_codes: dict[str, list[str]], product_data: dict, upd_dir: Path, output_path: Path | None = None) -> None:
    output_path = output_path or (upd_dir / "final_upd.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_rows = []
    row_index = 1

    for pdf_name, codes in formatted_codes.items():
        if not codes or pdf_name not in product_data:
            continue

        # Предполагаем, что product_data[pdf_name] — это кортеж или список кортежей
        data_list = product_data.get(pdf_name, [])
        if not data_list:
            continue

        # Берем первый набор данных (если несколько, нужно будет переработать логику)
        data = data_list[0] if isinstance(data_list, list) else data_list
        name, price, quantity, okei, vat, code_type = data

        # Преобразуем NDS: "none" → "без НДС"
        vat = "без НДС" if vat == "none" else vat

        if codes:
            csv_rows.append(f"{row_index},{name},{price},{quantity},{okei},{vat},{code_type},{codes[0]}")
            for code in codes[1:]:
                csv_rows.append(f"{row_index},,,,,,{code_type},{code}")
            row_index += 1

    if not csv_rows:
        print("Нет данных для создания CSV")
        return

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(csv_rows) + "\n")
    except Exception as e:
        print(f"Ошибка при записи CSV: {e}")
from pathlib import Path
import logging
import json
from typing import Dict, List

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_final_csv(reports_dir: Path, upd_dir: Path, output_path: Path | None = None) -> None:
    """
    Генерирует итоговый CSV-файл на основе отформатированных кодов и данных о товарах.
    Args:
        reports_dir (Path): Путь к папке с отчётами (ИТОГ/Отчеты о нанесении, содержит product_data.json).
        upd_dir (Path): Путь к папке с отформатированными кодами (ИТОГ/Для УПД, содержит <pdf_name>.txt).
        output_path (Path, optional): Путь для сохранения CSV. Если None, используется upd_dir/final_upd.csv.
    """
    #logging.info(f"Начинаю генерацию CSV-файла: {output_path or (upd_dir / 'final_upd.csv')}")
    output_path = output_path or (upd_dir / "final_upd.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Загружаем данные о товарах
    product_data_file = reports_dir / "product_data.json"
    product_data = {}
    try:
        with open(product_data_file, "r", encoding="utf-8") as f:
            product_data = json.load(f)
        #logging.info(f"Загружены данные о товарах из: {product_data_file}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке {product_data_file}: {e}. Завершение.")
        return

    # Проверяем режим (один товар или разные)
    is_single_product = product_data.get("is_single_product", False)
    #logging.info(f"Режим: {'Один товар' if is_single_product else 'Разные товары'}")

    csv_rows = []
    if is_single_product:
        # Для одного товара: первая строка полная, остальные только с кодами
        single_data = product_data.get("all", {})
        if not single_data:
            #logging.error("Данные для одного товара не найдены. Завершение.")
            return
        name, price, quantity, okei, vat, code_type = single_data
        vat = "без НДС" if vat == "none" else vat

        # Собираем все коды из всех файлов
        all_codes = []
        for txt_file in upd_dir.glob("*.txt"):
            if txt_file.name == "final_upd.csv":
                continue
            pdf_name = txt_file.stem
            try:
                #logging.info(f"Обрабатываю файл: {txt_file.name} (PDF: {pdf_name})")
                with open(txt_file, "r", encoding="utf-8") as f:
                    codes = [line.strip() for line in f if line.strip()]
                all_codes.extend(codes)
            except Exception as e:
                #logging.error(f"Ошибка при чтении {txt_file}: {e}. Пропускаю.")
                continue

        if not all_codes:
            #logging.error("Коды не найдены. CSV не создан.")
            return

        csv_rows.append(f"1,{name},{price},{quantity},{okei},{vat},{code_type},{all_codes[0]}")
        for code in all_codes[1:]:
            csv_rows.append(f"1,,,,,,{code_type},{code}")

    else:
        # Для разных товаров: индекс зависит от файла
        row_index = 1
        for txt_file in sorted(upd_dir.glob("*.txt")):
            if txt_file.name == "final_upd.csv":
                continue
            pdf_name = txt_file.stem
            data = product_data.get(pdf_name, {})
            if not data:
                #logging.warning(f"Данные о товаре для {pdf_name} не найдены. Пропускаю.")
                continue

            name, price, quantity, okei, vat, code_type = data
            vat = "без НДС" if vat == "none" else vat

            try:
                #logging.info(f"Обрабатываю файл: {txt_file.name} (PDF: {pdf_name}, индекс: {row_index})")
                with open(txt_file, "r", encoding="utf-8") as f:
                    codes = [line.strip() for line in f if line.strip()]
                if codes:
                    csv_rows.append(f"{row_index},{name},{price},{quantity},{okei},{vat},{code_type},{codes[0]}")
                    for code in codes[1:]:
                        csv_rows.append(f"{row_index},,,,,,{code_type},{code}")
                row_index += 1
            except Exception as e:
                #logging.error(f"Ошибка при чтении {txt_file}: {e}. Пропускаю.")
                continue

    if not csv_rows:
        #logging.error("Нет данных для записи в CSV. Завершение.")
        return

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(csv_rows) + "\n")
        #logging.info(f"CSV-файл успешно создан: {output_path}")
    except Exception as e:
        #logging.error(f"Ошибка при создании {output_path}: {e}")
        return
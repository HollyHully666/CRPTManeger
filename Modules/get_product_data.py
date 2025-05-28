from pathlib import Path
import logging
import json
from typing import Dict, Any

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _get_choice_from_options(prompt: str, options: list[tuple[str, Any]], display_key: int = 1) -> Any:
    logging.info(prompt)
    for i, option in enumerate(options, 1):
        logging.info(f"{i}) {option[display_key]}")
    while True:
        try:
            choice = input("Введите номер варианта: ")
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(options):
                return options[choice_idx][0]
            logging.warning(f"Некорректный выбор: {choice}. Попробуйте снова.")
        except ValueError:
            logging.warning(f"Некорректный ввод: {choice}. Введите число.")

def _get_single_product_data(file_name: str) -> tuple[str, float, float, str, str, str]:
    logging.info(f"Введите данные для файла: {file_name}")
    name = input("Наименование товара: ").strip()
    while not name:
        logging.warning("Наименование не может быть пустым.")
        name = input("Наименование товара: ").strip()

    while True:
        try:
            price = float(input("Стоимость товара (₽): "))
            if price >= 0:
                break
            logging.warning("Стоимость не может быть отрицательной.")
        except ValueError:
            logging.warning("Введите корректное число для стоимости.")

    while True:
        try:
            quantity = float(input("Количество: "))
            if quantity > 0:
                break
            logging.warning("Количество должно быть больше 0.")
        except ValueError:
            logging.warning("Введите корректное число для количества.")

    okei_options = [
        ("166", "Килограмм (166)"),
        ("796", "Штуки (796)"),
        ("112", "Литр (112)"),
    ]
    okei = _get_choice_from_options("Выберите единицу измерения:", okei_options)

    vat_options = [
        ("без НДС", "без НДС"),
        ("10%", "10"),
        ("20%", "20"),
    ]
    vat = _get_choice_from_options("Выберите ставку НДС:", vat_options)

    code_type_options = [
        ("КИЗ", "КИЗ"),
        ("НомУпак", "НомУпак"),
        ("ИдентТрансУпак", "ИдентТрансУпак"),
    ]
    code_type = _get_choice_from_options("Выберите тип кода:", code_type_options, display_key=0)

    return name, price, quantity, okei, vat, code_type

def get_product_data(uploaded_pdf_dir: Path, reports_dir: Path) -> Dict[str, Any]:
    """
    Запрашивает данные о товарах для PDF-файлов и сохраняет их в reports_dir/product_data.json.
    Args:
        uploaded_pdf_dir (Path): Путь к папке с PDF (source/ЗагруженныеPDF).
        reports_dir (Path): Путь к папке для отчётов (ИТОГ/Отчеты о нанесении).
    Returns:
        Dict[str, Any]: Словарь с данными о товарах.
    """
    pdf_files = list(uploaded_pdf_dir.glob("*.pdf"))
    #logging.info(f"Найдено PDF-файлов: {len(pdf_files)}")
    if not pdf_files:
        logging.error("PDF-файлы не найдены. Завершение.")
        return {}

    # Очищаем старые product_data.json
    product_data_file = reports_dir / "product_data.json"
    if product_data_file.exists():
        product_data_file.unlink()
        #logging.info(f"Удалён старый файл: {product_data_file}")

    pdf_names = [pdf.stem for pdf in pdf_files]
    product_data = {}

    options = [
        ("Один товар", "К одному товару"),
        ("Разные товары", "К разным"),
    ]
    single_product_choice = _get_choice_from_options("Загруженные PDF относятся к одному товару или разным?", options)

    if single_product_choice == "Один товар":
        data = _get_single_product_data("всех PDF-файлов")
        product_data["is_single_product"] = True
        product_data["all"] = data
        for pdf_name in pdf_names:
            product_data[pdf_name] = data
    else:
        product_data["is_single_product"] = False
        for pdf_name in pdf_names:
            data = _get_single_product_data(pdf_name)
            product_data[pdf_name] = data

    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        with open(product_data_file, "w", encoding="utf-8") as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)
        #logging.info(f"Данные о товарах сохранены в: {product_data_file}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении {product_data_file}: {e}")

    return product_data
from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import logging  # Импортируем модуль logging для логирования (будет удалён)
import json  # Импортируем модуль json для работы с JSON-файлами
from typing import Dict, List  # Импортируем типы Dict, List для аннотаций типов

def generate_final_csv(reports_dir: Path, upd_dir: Path, output_path: Path | None = None) -> None:  # Определяем функцию generate_final_csv, принимающую пути и возвращающую None
    output_path = output_path or (upd_dir / "final_upd.csv")  # Задаём output_path как переданный путь или upd_dir/final_upd.csv, если путь не указан
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Создаём родительскую папку для output_path, если её нет

    product_data_file = reports_dir / "product_data.json"  # Формируем путь к файлу product_data.json
    product_data = {}  # Инициализируем пустой словарь для хранения данных о товарах
    try:  # Начинаем блок try для обработки исключений при чтении файла
        with open(product_data_file, "r", encoding="utf-8") as f:  # Открываем файл product_data.json для чтения в кодировке UTF-8
            product_data = json.load(f)  # Загружаем данные из JSON-файла в словарь
    except Exception as e:  # Ловим любые исключения при чтении файла
        return  # В случае ошибки завершаем выполнение функции

    is_single_product = product_data.get("is_single_product", False)  # Получаем значение флага is_single_product из product_data (по умолчанию False)

    csv_rows = []  # Инициализируем пустой список для хранения строк CSV
    if is_single_product:  # Проверяем, установлен ли режим одного товара
        single_data = product_data.get("all", {})  # Получаем данные для одного товара из product_data (по умолчанию пустой словарь)
        if not single_data:  # Проверяем, есть ли данные для одного товара
            return  # Если данных нет, завершаем выполнение функции
        name, price, quantity, okei, vat, code_type = single_data  # Распаковываем данные товара в переменные
        vat = "без НДС" if vat == "none" else vat  # Преобразуем значение НДС: "none" заменяем на "без НДС", иначе оставляем как есть

        all_codes = []  # Инициализируем пустой список для хранения всех кодов
        for txt_file in upd_dir.glob("*.txt"):  # Цикл по всем .txt файлам в папке upd_dir
            if txt_file.name == "final_upd.csv":  # Проверяем, не является ли файл итоговым CSV
                continue  # Если это final_upd.csv, пропускаем файл
            pdf_name = txt_file.stem  # Извлекаем имя файла без расширения
            try:  # Начинаем блок try для обработки исключений при чтении файла
                with open(txt_file, "r", encoding="utf-8") as f:  # Открываем файл для чтения в кодировке UTF-8
                    codes = [line.strip() for line in f if line.strip()]  # Читаем строки, удаляем пробелы и отфильтровываем пустые
                all_codes.extend(codes)  # Добавляем коды из файла в общий список
            except Exception as e:  # Ловим любые исключения при чтении файла
                continue  # В случае ошибки пропускаем текущий файл

        if not all_codes:  # Проверяем, есть ли коды в списке
            return  # Если кодов нет, завершаем выполнение функции

        csv_rows.append(f"1,{name},{price},{quantity},{okei},{vat},{code_type},{all_codes[0]}")  # Добавляем первую строку CSV с полными данными и первым кодом
        for code in all_codes[1:]:  # Цикл по остальным кодам, начиная со второго
            csv_rows.append(f"1,,,,,,{code_type},{code}")  # Добавляем строки CSV только с типом кода и кодом

    else:  # Если режим для разных товаров
        row_index = 1  # Инициализируем индекс строки как 1
        for txt_file in sorted(upd_dir.glob("*.txt")):  # Цикл по всем .txt файлам в папке upd_dir, отсортированным по имени
            if txt_file.name == "final_upd.csv":  # Проверяем, не является ли файл итоговым CSV
                continue  # Если это final_upd.csv, пропускаем файл
            pdf_name = txt_file.stem  # Извлекаем имя файла без расширения
            data = product_data.get(pdf_name, {})  # Получаем данные для текущего PDF из product_data (по умолчанию пустой словарь)
            if not data:  # Проверяем, есть ли данные для текущего PDF
                continue  # Если данных нет, пропускаем текущий файл

            name, price, quantity, okei, vat, code_type = data  # Распаковываем данные товара в переменные
            vat = "без НДС" if vat == "none" else vat  # Преобразуем значение НДС: "none" заменяем на "без НДС", иначе оставляем как есть

            try:  # Начинаем блок try для обработки исключений при чтении файла
                with open(txt_file, "r", encoding="utf-8") as f:  # Открываем файл для чтения в кодировке UTF-8
                    codes = [line.strip() for line in f if line.strip()]  # Читаем строки, удаляем пробелы и отфильтровываем пустые
                if codes:  # Проверяем, есть ли коды в списке
                    csv_rows.append(f"{row_index},{name},{price},{quantity},{okei},{vat},{code_type},{codes[0]}")  # Добавляем первую строку CSV с полными данными и первым кодом
                    for code in codes[1:]:  # Цикл по остальным кодам, начиная со второго
                        csv_rows.append(f"{row_index},,,,,,{code_type},{code}")  # Добавляем строки CSV только с типом кода и кодом
                row_index += 1  # Увеличиваем индекс строки на 1
            except Exception as e:  # Ловим любые исключения при чтении файла
                continue  # В случае ошибки пропускаем текущий файл

    if not csv_rows:  # Проверяем, есть ли строки для записи в CSV
        return  # Если строк нет, завершаем выполнение функции

    try:  # Начинаем блок try для обработки исключений при записи файла
        with open(output_path, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
            f.write("\n".join(csv_rows) + "\n")  # Записываем все строки CSV в файл, разделяя их переносами строки
    except Exception as e:  # Ловим любые исключения при записи файла
        return  # В случае ошибки завершаем выполнение функции
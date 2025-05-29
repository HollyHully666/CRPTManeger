from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
import json  # Импортируем модуль json для работы с JSON-файлами
from typing import Dict, Any, List  # Импортируем типы Dict, Any для аннотаций типов

def _get_choice_from_options(prompt: str, options: list[tuple[str, Any]], display_key: int = 1) -> Any:  # Определяем функцию _get_choice_from_options, принимающую запрос, список опций и ключ отображения, возвращающую значение
    for i, option in enumerate(options, 1):  # Цикл по опциям с нумерацией, начиная с 1
        print(f"{i}) {option[display_key]}")  # Выводим номер и значение опции по указанному ключу
    while True:  # Начинаем бесконечный цикл для ввода выбора
        try:  # Начинаем блок try для обработки исключений
            choice = input("Введите номер варианта: ")  # Запрашиваем ввод номера варианта
            choice_idx = int(choice) - 1  # Преобразуем введённый номер в индекс (уменьшаем на 1)
            if 0 <= choice_idx < len(options):  # Проверяем, находится ли индекс в допустимом диапазоне
                return options[choice_idx][0]  # Возвращаем первый элемент кортежа опции по выбранному индексу
        except ValueError:  # Ловим ошибку, если ввод не является числом
            pass  # Пропускаем некорректный ввод

def _get_single_product_data(file_name: str, extracted_codes_by_pdf: Dict[str, List[str]] = None, pdf_name: str = None) -> tuple[str, float, float, str, str, str]:  # Определяем функцию _get_single_product_data, принимающую имя файла, словарь кодов и имя PDF, возвращающую кортеж данных
    print(f"Введите данные для файла: {file_name}")  # Выводим запрос на ввод данных для указанного файла
    name = input("Наименование товара: ").strip()  # Запрашиваем наименование товара и удаляем пробелы
    while not name:  # Проверяем, пустое ли наименование
        name = input("Наименование товара: ").strip()  # Запрашиваем наименование снова, если оно пустое

    while True:  # Начинаем бесконечный цикл для ввода стоимости
        try:  # Начинаем блок try для обработки исключений
            price = float(input("Стоимость товара (₽): "))  # Запрашиваем стоимость и преобразуем в float
            if price >= 0:  # Проверяем, неотрицательная ли стоимость
                break  # Выходим из цикла, если стоимость корректна
        except ValueError:  # Ловим ошибку, если ввод не является числом
            pass  # Пропускаем некорректный ввод

    # Определяем количество на основе extracted_codes_by_pdf и single_product_choice
    if extracted_codes_by_pdf is not None:  # Проверяем, передан ли словарь extracted_codes_by_pdf
        if file_name == "всех PDF-файлов":  # Проверяем, если данные для всех PDF-файлов
            quantity = sum(len(codes) for codes in extracted_codes_by_pdf.values())  # Вычисляем общее количество кодов из всех подпапок
        else:  # Если данные для конкретного PDF
            quantity = len(extracted_codes_by_pdf.get(pdf_name, []))  # Берем количество кодов для конкретной подпапки PDF
    else:  # Если extracted_codes_by_pdf не передан
        while True:  # Начинаем бесконечный цикл для ввода количества
            try:  # Начинаем блок try для обработки исключений
                quantity = float(input("Количество: "))  # Запрашиваем количество и преобразуем в float
                if quantity > 0:  # Проверяем, положительное ли количество
                    break  # Выходим из цикла, если количество корректно
            except ValueError:  # Ловим ошибку, если ввод не является числом
                pass  # Пропускаем некорректный ввод

    okei_options = [  # Определяем список опций для единиц измерения
        ("166", "Килограмм (166)"),  # Опция для килограмма
        ("796", "Штуки (796)"),  # Опция для штук
        ("112", "Литр (112)"),  # Опция для литра
    ]  # Закрывающая скобка списка опций
    okei = _get_choice_from_options("Выберите единицу измерения:", okei_options)  # Запрашиваем выбор единицы измерения

    vat_options = [  # Определяем список опций для ставок НДС
        ("без НДС", "без НДС"),  # Опция для ставки без НДС
        ("10%", "10"),  # Опция для ставки 10%
        ("20%", "20"),  # Опция для ставки 20%
    ]  # Закрывающая скобка списка опций
    vat = _get_choice_from_options("Выберите ставку НДС:", vat_options)  # Запрашиваем выбор ставки НДС

    code_type_options = [  # Определяем список опций для типов кодов
        ("КИЗ", "КИЗ"),  # Опция для типа КИЗ
        ("НомУпак", "НомУпак"),  # Опция для типа НомУпак
        ("ИдентТрансУпак", "ИдентТрансУпак"),  # Опция для типа ИдентТрансУпак
    ]  # Закрывающая скобка списка опций
    code_type = _get_choice_from_options("Выберите тип кода:", code_type_options, display_key=0)  # Запрашиваем выбор типа кода с отображением первого элемента

    return name, price, quantity, okei, vat, code_type  # Возвращаем кортеж с наименованием, стоимостью, количеством, ОКЕИ, НДС и типом кода

def get_product_data(uploaded_pdf_dir: Path, reports_dir: Path, extracted_codes_by_pdf: Dict[str, List[str]] = None) -> Dict[str, Any]:  # Определяем функцию get_product_data, принимающую пути и словарь кодов, возвращающую словарь
    pdf_files = list(uploaded_pdf_dir.glob("*.pdf"))  # Ищем все PDF-файлы в uploaded_pdf_dir и преобразуем в список
    if not pdf_files:  # Проверяем, есть ли PDF-файлы в списке
        return {}  # Если файлов нет, возвращаем пустой словарь

    product_data_file = reports_dir / "product_data.json"  # Формируем путь к файлу product_data.json
    if product_data_file.exists():  # Проверяем, существует ли файл
        product_data_file.unlink()  # Если файл существует, удаляем его

    pdf_names = [pdf.stem for pdf in pdf_files]  # Извлекаем имена PDF-файлов без расширений
    product_data = {}  # Инициализируем пустой словарь для хранения данных о товарах

    options = [  # Определяем список опций для выбора типа обработки
        ("Один товар", "К одному товару"),  # Опция для одного товара
        ("Разные товары", "К разным"),  # Опция для разных товаров
    ]  # Закрывающая скобка списка опций
    single_product_choice = _get_choice_from_options("Загруженные PDF относятся к одному товару или разным?", options)  # Запрашиваем выбор типа обработки

    if single_product_choice == "Один товар":  # Проверяем, выбран ли вариант "Один товар"
        data = _get_single_product_data("всех PDF-файлов", extracted_codes_by_pdf)  # Запрашиваем данные для всех PDF-файлов с передачей словаря кодов
        product_data["is_single_product"] = True  # Устанавливаем флаг, что используется один товар
        product_data["all"] = data  # Сохраняем данные для всех файлов
        for pdf_name in pdf_names:  # Цикл по именам PDF-файлов
            product_data[pdf_name] = data  # Добавляем данные для каждого PDF-файла
    else:  # Если выбран вариант "Разные товары"
        product_data["is_single_product"] = False  # Устанавливаем флаг, что используются разные товары
        for pdf_name in pdf_names:  # Цикл по именам PDF-файлов
            data = _get_single_product_data(pdf_name, extracted_codes_by_pdf, pdf_name)  # Запрашиваем данные для каждого PDF-файла с передачей имени PDF
            product_data[pdf_name] = data  # Сохраняем данные для текущего PDF-файла

    try:  # Начинаем блок try для обработки исключений при записи файла
        reports_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку reports_dir, включая родительские, если их нет
        with open(product_data_file, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
            json.dump(product_data, f, ensure_ascii=False, indent=2)  # Записываем данные в JSON с красивым форматированием
    except Exception as e:  # Ловим любые исключения при записи файла
        pass  # Пропускаем ошибку (логирование удалено)

    return product_data  # Возвращаем словарь с данными о товарах
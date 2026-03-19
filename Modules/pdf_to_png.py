from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
from pdf2image import convert_from_path  # Импортируем функцию convert_from_path из pdf2image для конвертации PDF в изображения
from multiprocessing import Pool, cpu_count  # Импортируем Pool и cpu_count из multiprocessing для параллельной обработки
from typing import Dict, List, Tuple  # Импортируем типы Dict, List, Tuple для аннотаций типов
import shutil  # Импортируем модуль shutil для операций с файлами и папками

def _convert_single_pdf(args: Tuple[Path, Path, str | None]) -> Tuple[str, List[Path]]:  # Определяем функцию _convert_single_pdf, принимающую кортеж и возвращающую кортеж с именем PDF и списком путей
    pdf_path, data_matrix_dir, poppler_path = args  # Распаковываем кортеж аргументов в переменные: путь к PDF, путь к папке DATA MATRIX, путь к Poppler
    pdf_name = pdf_path.stem  # Извлекаем имя PDF-файла без расширения
    image_dir = data_matrix_dir / pdf_name  # Создаём путь к подпапке с именем PDF внутри data_matrix_dir
    image_paths = []  # Инициализируем пустой список для хранения путей к PNG-файлам
    try:  # Начинаем блок try для обработки исключений
        if image_dir.exists():  # Проверяем, существует ли папка image_dir
            shutil.rmtree(image_dir)  # Если папка существует, удаляем её со всем содержимым
        image_dir.mkdir(parents=True, exist_ok=True)  # Создаём папку image_dir, включая родительские папки, если их нет
        
        images = convert_from_path(  # Конвертируем PDF в список изображений
            pdf_path=pdf_path,  # Указываем путь к PDF-файлу
            dpi=300,  # Увеличиваем разрешение до 300 DPI для лучшего распознавания
            poppler_path=poppler_path,  # Указываем путь к Poppler, если передан
            thread_count=4  # Устанавливаем количество потоков для конвертации
        )  # Закрывающая скобка для вызова convert_from_path
        for i, image in enumerate(images, start=1):  # Цикл по изображениям с индексацией начиная с 1
            image_path = image_dir / f"{pdf_name}_{i}.png"  # Формируем путь для сохранения PNG-файла (имя PDF + номер страницы)
            image.save(image_path, "PNG", optimize=True)  # Сохраняем изображение как PNG с оптимизацией
            image_paths.append(image_path)  # Добавляем путь к PNG-файлу в список image_paths
        return pdf_name, image_paths  # Возвращаем кортеж с именем PDF и списком путей к PNG-файлам
    except Exception as e:  # Ловим любые исключения в блоке except
        return pdf_name, []  # Возвращаем кортеж с именем PDF и пустым списком в случае ошибки

def convert_pdf_to_images(uploaded_pdf_dir: Path, data_matrix_dir: Path, poppler_path: str | None = None) -> Dict[str, List[Path]]:  # Определяем функцию convert_pdf_to_images, принимающую пути и возвращающую словарь
    processed_pdfs_info = {}  # Инициализируем пустой словарь для хранения информации о обработанных PDF
    pdf_files = list(uploaded_pdf_dir.glob("*.pdf"))  # Ищем все PDF-файлы в папке uploaded_pdf_dir и преобразуем в список
    if not pdf_files:  # Проверяем, есть ли PDF-файлы в списке
        return processed_pdfs_info  # Если PDF-файлов нет, возвращаем пустой словарь

    for item in data_matrix_dir.iterdir():  # Цикл по всем элементам в папке data_matrix_dir
        if item.is_dir():  # Проверяем, является ли элемент папкой
            shutil.rmtree(item)  # Если это папка, удаляем её со всем содержимым
    
    num_processes = max(1, cpu_count() - 1)  # Определяем количество процессов как число ядер процессора минус 1, но не меньше 1
    args = [(pdf_file, data_matrix_dir, poppler_path) for pdf_file in pdf_files]  # Создаём список кортежей аргументов для каждого PDF-файла

    with Pool(processes=num_processes) as pool:  # Создаём пул процессов с заданным количеством процессов
        results = pool.map(_convert_single_pdf, args)  # Выполняем параллельную обработку PDF-файлов с помощью _convert_single_pdf

    for pdf_name, image_paths in results:  # Цикл по результатам обработки PDF-файлов
        if image_paths:  # Проверяем, есть ли пути к PNG-файлам в результате
            processed_pdfs_info[pdf_name] = image_paths  # Если пути есть, добавляем их в словарь processed_pdfs_info

    return processed_pdfs_info  # Возвращаем словарь с именами PDF и списками путей к PNG-файлам
from pathlib import Path  # Импортируем модуль Path для работы с файловыми путями
from PIL import Image  # Импортируем класс Image из PIL для работы с изображениями
from pylibdmtx.pylibdmtx import decode as dmtx_decode  # Импортируем функцию decode из pylibdmtx и переименовываем её в dmtx_decode для распознавания DataMatrix-кодов
from multiprocessing import Pool, cpu_count  # Импортируем Pool и cpu_count из multiprocessing для параллельной обработки
from typing import Dict, List, Tuple  # Импортируем типы Dict, List, Tuple для аннотаций типов
import numpy as np  # Импортируем numpy для работы с массивами

def process_chunk(chunk: List[Path]) -> List[Tuple[str, List[str]]]:  # Определяем функцию process_chunk, которая принимает список путей и возвращает список кортежей
    return [_decode_image(img) for img in chunk]  # Применяем _decode_image к каждому пути в chunk и возвращаем список результатов

def _decode_image(image_path: Path) -> Tuple[str, List[str]]:  # Определяем функцию _decode_image, которая принимает путь к изображению и возвращает кортеж с именем файла и списком кодов
    codes = []  # Инициализируем пустой список для хранения извлечённых кодов
    try:  # Начинаем блок try для обработки исключений
        img = Image.open(image_path).convert('L')  # Открываем изображение по пути и конвертируем в оттенки серого ('L')
        img_np = np.array(img)  # Преобразуем изображение в массив numpy
        img_np = np.clip(img_np * 1.2, 0, 255).astype(np.uint8)  # Увеличиваем яркость на 20%, ограничиваем значения от 0 до 255, конвертируем в тип uint8
        decoded_objects = dmtx_decode(img_np, timeout=300, max_count=1, shrink=2)  # Распознаём DataMatrix-коды в изображении с таймаутом 300 мс, максимум 1 код, уменьшением в 2 раза
        codes = [obj.data.decode('utf-8') for obj in decoded_objects]  # Извлекаем данные из распознанных объектов и декодируем их в строку UTF-8
        return image_path.name, codes  # Возвращаем кортеж с именем файла и списком кодов
    except Exception as e:  # Ловим любые исключения в блоке except
        return image_path.name, []  # Возвращаем кортеж с именем файла и пустым списком в случае ошибки

def extract_datamatrix_from_image(data_matrix_dir: Path, reports_dir: Path) -> Dict[str, List[str]]:  # Определяем функцию extract_datamatrix_from_image, принимающую пути и возвращающую словарь
    extracted_codes_by_pdf = {}  # Инициализируем пустой словарь для хранения кодов по PDF

    pdf_dirs = [d for d in data_matrix_dir.iterdir() if d.is_dir()]  # Создаём список подпапок в data_matrix_dir
    if not pdf_dirs:  # Проверяем, есть ли подпапки
        return extracted_codes_by_pdf  # Если подпапок нет, возвращаем пустой словарь

    num_processes = max(1, cpu_count() - 1)  # Определяем количество процессов как число ядер процессора минус 1, но не меньше 1

    for pdf_dir in pdf_dirs:  # Цикл по всем подпапкам в data_matrix_dir
        pdf_name = pdf_dir.name  # Извлекаем имя текущей подпапки (имя PDF)

        image_files = list(pdf_dir.glob("*.png"))  # Ищем все PNG-файлы в текущей подпапке и преобразуем в список
        if not image_files:  # Проверяем, есть ли PNG-файлы
            continue  # Если PNG-файлов нет, пропускаем текущую подпапку

        chunk_size = max(1, len(image_files) // num_processes + 1)  # Вычисляем размер блока для разделения файлов на части (не менее 1)
        image_chunks = [image_files[i:i + chunk_size] for i in range(0, len(image_files), chunk_size)]  # Делим список файлов на блоки размером chunk_size

        with Pool(processes=num_processes) as pool:  # Создаём пул процессов с заданным количеством процессов
            results = pool.map(process_chunk, image_chunks)  # Выполняем параллельную обработку блоков с помощью process_chunk

        codes = []  # Инициализируем пустой список для хранения всех кодов из текущей подпапки
        for chunk_result in results:  # Цикл по результатам обработки блоков
            for image_name, image_codes in chunk_result:  # Цикл по результатам обработки каждого изображения в блоке
                if image_codes:  # Проверяем, есть ли коды в результате обработки
                    codes.extend(image_codes)  # Если коды есть, добавляем их в общий список codes

        if codes:  # Проверяем, были ли найдены коды в текущей подпапке
            extracted_codes_by_pdf[pdf_name] = codes  # Если коды есть, добавляем их в словарь extracted_codes_by_pdf
            output_file = reports_dir / f"{pdf_name}.txt"  # Формируем путь для файла отчёта с именем PDF и расширением .txt
            try:  # Начинаем блок try для обработки исключений при записи файла
                output_file.parent.mkdir(parents=True, exist_ok=True)  # Создаём родительскую папку для файла отчёта, если её нет
                with open(output_file, "w", encoding="utf-8") as f:  # Открываем файл для записи в кодировке UTF-8
                    f.write("\n".join(codes))  # Записываем все коды в файл, разделяя их переносом строки
            except OSError as e:  # Ловим ошибки ввода-вывода при записи файла
                pass  # Ничего не делаем в случае ошибки (логирование удалено)

    return extracted_codes_by_pdf  # Возвращаем словарь с именами PDF и списками извлечённых кодов
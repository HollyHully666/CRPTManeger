from pathlib import Path
import logging
from PIL import Image
from pylibdmtx.pylibdmtx import decode as dmtx_decode
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Tuple
import numpy as np

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_chunk(chunk: List[Path]) -> List[Tuple[str, List[str]]]:
    return [_decode_image(img) for img in chunk]

def _decode_image(image_path: Path) -> Tuple[str, List[str]]:
    """Обрабатывает одно изображение и возвращает имя файла и список кодов."""
    codes = []
    try:
        img = Image.open(image_path).convert('L')
        img_np = np.array(img)
        img_np = np.clip(img_np * 1.2, 0, 255).astype(np.uint8)
        decoded_objects = dmtx_decode(img_np, timeout=300, max_count=1, shrink=2)
        codes = [obj.data.decode('utf-8') for obj in decoded_objects]
        return image_path.name, codes
    except Exception as e:
        #logging.error(f"Ошибка при обработке {image_path}: {e}")
        return image_path.name, []

def extract_datamatrix_from_image(data_matrix_dir: Path, reports_dir: Path) -> Dict[str, List[str]]:
    """
    Извлекает DataMatrix-коды из PNG-файлов в подпапках data_matrix_dir.
    Сохраняет коды в reports_dir/<pdf_name>.txt.
    Args:
        data_matrix_dir (Path): Путь к папке с PNG (source/DATA MATRIX).
        reports_dir (Path): Путь к папке для отчётов (ИТОГ/Отчеты о нанесении).
    Returns:
        Dict[str, List[str]]: Словарь с именами PDF и списками кодов.
    """
    #logging.info(f"Начинаю извлечение DataMatrix-кодов из: {data_matrix_dir}")
    extracted_codes_by_pdf = {}

    pdf_dirs = [d for d in data_matrix_dir.iterdir() if d.is_dir()]
    if not pdf_dirs:
        #logging.warning(f"Не найдено подпапок с изображениями в {data_matrix_dir}")
        return extracted_codes_by_pdf

    num_processes = max(1, cpu_count() - 1)
    #logging.info(f"Использую {num_processes} процессов для параллельной обработки")

    for pdf_dir in pdf_dirs:
        pdf_name = pdf_dir.name
        #logging.info(f"Обрабатываю папку изображений: {pdf_name}")

        image_files = list(pdf_dir.glob("*.png"))
        if not image_files:
            #logging.warning(f"Не найдено изображений в {pdf_dir}. Пропускаю.")
            continue

        chunk_size = max(1, len(image_files) // num_processes + 1)
        image_chunks = [image_files[i:i + chunk_size] for i in range(0, len(image_files), chunk_size)]

        with Pool(processes=num_processes) as pool:
            results = pool.map(process_chunk, image_chunks)

        codes = []
        for chunk_result in results:
            for image_name, image_codes in chunk_result:
                if image_codes:
                    codes.extend(image_codes)
                    #logging.info(f"[{image_name}]: Извлечено кодов: {len(image_codes)}")
                else:
                    logging.info(f"[{image_name}]: Коды не найдены")

        if codes:
            extracted_codes_by_pdf[pdf_name] = codes
            output_file = reports_dir / f"{pdf_name}.txt"
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(codes))
                #logging.info(f"Коды сохранены в: {output_file}")
            except OSError as e:
                logging.error(f"Ошибка при сохранении {output_file}: {e}")
        else:
            logging.warning(f"Для папки '{pdf_name}' не найдено кодов. Файл отчетов не создан.")

    return extracted_codes_by_pdf